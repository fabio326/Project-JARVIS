import Foundation
import Speech
import AVFoundation
import Combine

/// Handles microphone speech recognition and spoken responses for JARVIS.
@MainActor
final class SpeechManager: NSObject, ObservableObject {
    @Published var transcript = ""
    @Published var isListening = false
    @Published var isSpeaking = false
    @Published var authorizationError: String?

    /// Called once when speech ends automatically via silence detection or a final result.
    var onSpeechFinished: ((String) -> Void)?

    private let speechRecognizer = SFSpeechRecognizer(locale: Locale(identifier: "en-US"))
    private let audioEngine = AVAudioEngine()
    private let synthesizer = AVSpeechSynthesizer()

    private var recognitionRequest: SFSpeechAudioBufferRecognitionRequest?
    private var recognitionTask: SFSpeechRecognitionTask?

    // Silence detection state.
    private let silenceDuration: TimeInterval = 1.2
    private var silenceTimerWorkItem: DispatchWorkItem?
    private var hasCalledSpeechFinished = false
    private var hasRecognizedMeaningfulSpeech = false

    override init() {
        super.init()
        synthesizer.delegate = self
    }

    /// Ask for speech-recognition and microphone access before listening.
    func requestAuthorization() async -> Bool {
        authorizationError = nil

        let speechStatus = await withCheckedContinuation { continuation in
            SFSpeechRecognizer.requestAuthorization { status in
                continuation.resume(returning: status)
            }
        }

        guard speechStatus == .authorized else {
            authorizationError = "Speech recognition permission was denied."
            return false
        }

        let microphoneGranted = await requestMicrophonePermission()
        guard microphoneGranted else {
            authorizationError = "Microphone permission was denied."
            return false
        }

        return true
    }

    /// Begin live transcription from the microphone.
    func startListening() {
        guard !isListening else { return }

        guard let speechRecognizer, speechRecognizer.isAvailable else {
            authorizationError = "Speech recognition is unavailable right now."
            return
        }

        cleanupRecognition()
        stopSpeaking()

        transcript = ""
        authorizationError = nil
        hasCalledSpeechFinished = false
        hasRecognizedMeaningfulSpeech = false

        let request = SFSpeechAudioBufferRecognitionRequest()
        request.shouldReportPartialResults = true
        recognitionRequest = request

        let inputNode = audioEngine.inputNode
        let recordingFormat = inputNode.outputFormat(forBus: 0)

        inputNode.installTap(onBus: 0, bufferSize: 1024, format: recordingFormat) { buffer, _ in
            request.append(buffer)
        }

        recognitionTask = speechRecognizer.recognitionTask(with: request) { [weak self] result, error in
            Task { @MainActor in
                guard let self else { return }

                if let result {
                    let newText = result.bestTranscription.formattedString
                        .trimmingCharacters(in: .whitespacesAndNewlines)

                    if !newText.isEmpty {
                        // Partial results update continuously while the user is speaking.
                        self.transcript = newText

                        // Ignore brief microphone noise until real words appear.
                        if newText.count >= 2 {
                            self.hasRecognizedMeaningfulSpeech = true
                            self.resetSilenceTimer()
                        }
                    }

                    if result.isFinal {
                        self.finishListeningAfterSpeech()
                    }
                }

                if let error {
                    // Ignore cancellation errors from a normal stop.
                    let nsError = error as NSError
                    if nsError.domain != "kAFAssistantErrorDomain" || nsError.code != 216 {
                        self.authorizationError = error.localizedDescription
                    }
                    self.cleanupRecognition()
                }
            }
        }

        do {
            audioEngine.prepare()
            try audioEngine.start()
            isListening = true
        } catch {
            authorizationError = "Could not start the microphone."
            cleanupRecognition()
        }
    }

    /// Stop listening manually without triggering the automatic completion callback.
    func stopListening() {
        cleanupRecognition()
    }

    /// Read JARVIS text aloud using a natural English voice.
    func speak(_ text: String) {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }

        stopSpeaking()

        let utterance = AVSpeechUtterance(string: trimmed)
        utterance.voice = preferredEnglishVoice()
        utterance.rate = AVSpeechUtteranceDefaultSpeechRate

        isSpeaking = true
        synthesizer.speak(utterance)
    }

    /// Stop any in-progress spoken response.
    func stopSpeaking() {
        if synthesizer.isSpeaking {
            synthesizer.stopSpeaking(at: .immediate)
        }
        isSpeaking = false
    }

    private func requestMicrophonePermission() async -> Bool {
        if #available(macOS 14.0, *) {
            return await AVAudioApplication.requestRecordPermission()
        }

        return await withCheckedContinuation { continuation in
            AVCaptureDevice.requestAccess(for: .audio) { granted in
                continuation.resume(returning: granted)
            }
        }
    }

    private func preferredEnglishVoice() -> AVSpeechSynthesisVoice? {
        let voices = AVSpeechSynthesisVoice.speechVoices()
        let englishVoices = voices.filter { $0.language.hasPrefix("en") }

        let preferredNames = ["Samantha", "Alex", "Daniel", "Karen", "Moira"]
        for name in preferredNames {
            if let voice = englishVoices.first(where: { $0.name.contains(name) }) {
                return voice
            }
        }

        return AVSpeechSynthesisVoice(language: "en-US")
    }

    /// Restart the silence countdown whenever new meaningful speech is recognized.
    private func resetSilenceTimer() {
        cancelSilenceTimer()

        let workItem = DispatchWorkItem { [weak self] in
            Task { @MainActor in
                self?.handleSilenceDetected()
            }
        }

        silenceTimerWorkItem = workItem
        DispatchQueue.main.asyncAfter(deadline: .now() + silenceDuration, execute: workItem)
    }

    private func cancelSilenceTimer() {
        silenceTimerWorkItem?.cancel()
        silenceTimerWorkItem = nil
    }

    private func handleSilenceDetected() {
        guard isListening else { return }
        guard hasRecognizedMeaningfulSpeech else { return }
        finishListeningAfterSpeech()
    }

    /// End listening after silence or a final recognition result and notify once.
    private func finishListeningAfterSpeech() {
        guard !hasCalledSpeechFinished else { return }
        guard isListening else { return }

        let finalTranscript = transcript.trimmingCharacters(in: .whitespacesAndNewlines)

        cancelSilenceTimer()

        if audioEngine.isRunning {
            audioEngine.stop()
        }

        audioEngine.inputNode.removeTap(onBus: 0)
        recognitionRequest?.endAudio()
        recognitionTask?.cancel()

        recognitionRequest = nil
        recognitionTask = nil
        isListening = false
        hasRecognizedMeaningfulSpeech = false

        guard !finalTranscript.isEmpty else { return }

        hasCalledSpeechFinished = true
        onSpeechFinished?(finalTranscript)
    }

    private func cleanupRecognition() {
        cancelSilenceTimer()

        if audioEngine.isRunning {
            audioEngine.stop()
        }

        audioEngine.inputNode.removeTap(onBus: 0)
        recognitionRequest?.endAudio()
        recognitionTask?.cancel()

        recognitionRequest = nil
        recognitionTask = nil
        isListening = false
        hasRecognizedMeaningfulSpeech = false
    }
}

extension SpeechManager: AVSpeechSynthesizerDelegate {
    nonisolated func speechSynthesizer(
        _ synthesizer: AVSpeechSynthesizer,
        didStart utterance: AVSpeechUtterance
    ) {
        Task { @MainActor in
            isSpeaking = true
        }
    }

    nonisolated func speechSynthesizer(
        _ synthesizer: AVSpeechSynthesizer,
        didFinish utterance: AVSpeechUtterance
    ) {
        Task { @MainActor in
            isSpeaking = false
        }
    }

    nonisolated func speechSynthesizer(
        _ synthesizer: AVSpeechSynthesizer,
        didCancel utterance: AVSpeechUtterance
    ) {
        Task { @MainActor in
            isSpeaking = false
        }
    }
}
