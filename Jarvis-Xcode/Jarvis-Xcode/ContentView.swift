import SwiftUI

struct ChatResponse: Decodable {
    let response: String
}

struct ContentView: View {
    @StateObject private var speechManager = SpeechManager()

    @State private var message = ""
    @State private var jarvisResponse = "Good evening, Fabio."
    @State private var isThinking = false

    var body: some View {
        ZStack {
            Color.black
                .ignoresSafeArea()

            VStack(spacing: 24) {
                Spacer()

                Text("JARVIS")
                    .font(.system(size: 34, weight: .light, design: .rounded))
                    .tracking(10)
                    .foregroundStyle(.white)

                Button(action: handleOrbTap) {
                    ZStack {
                        Circle()
                            .stroke(orbStrokeColor, lineWidth: 2)
                            .frame(width: 150, height: 150)

                        Circle()
                            .fill(orbFillColor)
                            .frame(width: 105, height: 105)
                            .scaleEffect(orbScale)
                            .animation(orbAnimation, value: orbAnimationValue)

                        Image(systemName: speechManager.isListening ? "mic.fill" : "waveform")
                            .font(.system(size: 34))
                            .foregroundStyle(.white)
                    }
                }
                .buttonStyle(.plain)
                .disabled(isThinking)

                Text(voiceStatusText)
                    .font(.caption)
                    .foregroundStyle(.white.opacity(0.55))

                if speechManager.isListening {
                    Text("Listening...")
                        .font(.subheadline)
                        .foregroundStyle(.white.opacity(0.75))
                }

                if let authorizationError = speechManager.authorizationError {
                    Text(authorizationError)
                        .font(.caption)
                        .foregroundStyle(.red.opacity(0.85))
                        .multilineTextAlignment(.center)
                        .frame(maxWidth: 420)
                }

                ScrollView {
                    Text(jarvisResponse)
                        .font(.system(size: 18, weight: .regular))
                        .foregroundStyle(.white.opacity(0.9))
                        .multilineTextAlignment(.center)
                        .frame(maxWidth: 560)
                        .padding()
                }
                .frame(height: 150)

                HStack(spacing: 12) {
                    TextField("Ask JARVIS anything...", text: $message)
                        .textFieldStyle(.plain)
                        .padding(14)
                        .background(.white.opacity(0.08))
                        .clipShape(RoundedRectangle(cornerRadius: 14))
                        .foregroundStyle(.white)
                        .onSubmit {
                            sendMessage()
                        }

                    Button {
                        sendMessage()
                    } label: {
                        Image(systemName: "arrow.up")
                            .font(.system(size: 17, weight: .semibold))
                            .frame(width: 42, height: 42)
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(message.trimmingCharacters(in: .whitespaces).isEmpty || isThinking)
                }
                .frame(maxWidth: 620)
                .onChange(of: speechManager.transcript) { _, newValue in
                    if speechManager.isListening {
                        message = newValue
                    }
                }

                HStack(spacing: 22) {
                    statusItem("Brain", active: true)
                    statusItem("Memory", active: true)
                    statusItem("Mac Control", active: true)
                    statusItem(
                        "Voice",
                        active: speechManager.isListening || speechManager.isSpeaking
                    )
                }

                Spacer()
            }
            .padding(40)
        }
        .frame(minWidth: 850, minHeight: 620)
    }

    private var voiceStatusText: String {
        if isThinking {
            return "Thinking"
        }
        if speechManager.isSpeaking {
            return "Speaking"
        }
        if speechManager.isListening {
            return "Listening"
        }
        return "Ready"
    }

    private var orbFillColor: Color {
        if isThinking {
            return .white.opacity(0.28)
        }
        if speechManager.isListening {
            return .white.opacity(0.30)
        }
        if speechManager.isSpeaking {
            return .white.opacity(0.22)
        }
        return .white.opacity(0.12)
    }

    private var orbStrokeColor: Color {
        if speechManager.isListening {
            return .white.opacity(0.35)
        }
        return .white.opacity(0.12)
    }

    private var orbScale: CGFloat {
        if isThinking {
            return 1.08
        }
        if speechManager.isListening {
            return 1.06
        }
        if speechManager.isSpeaking {
            return 1.04
        }
        return 1.0
    }

    private var orbAnimationValue: Bool {
        isThinking || speechManager.isListening || speechManager.isSpeaking
    }

    private var orbAnimation: Animation? {
        if orbAnimationValue {
            return .easeInOut(duration: 0.8).repeatForever(autoreverses: true)
        }
        return .default
    }

    private func statusItem(_ title: String, active: Bool) -> some View {
        HStack(spacing: 7) {
            Circle()
                .fill(active ? .green : .gray)
                .frame(width: 7, height: 7)

            Text(title)
                .font(.caption)
                .foregroundStyle(.white.opacity(0.65))
        }
    }

    private func handleOrbTap() {
        if speechManager.isListening {
            speechManager.stopListening()

            let trimmedTranscript = speechManager.transcript
                .trimmingCharacters(in: .whitespacesAndNewlines)

            guard !trimmedTranscript.isEmpty else {
                return
            }

            message = trimmedTranscript
            sendMessage()
            return
        }

        if speechManager.isSpeaking {
            speechManager.stopSpeaking()
        }

        Task {
            let authorized = await speechManager.requestAuthorization()
            guard authorized else { return }
            speechManager.startListening()
        }
    }

    private func sendMessage() {
        let trimmedMessage = message.trimmingCharacters(in: .whitespacesAndNewlines)

        guard !trimmedMessage.isEmpty else {
            return
        }

        message = ""
        isThinking = true
        jarvisResponse = "Thinking..."

        guard let url = URL(string: "http://127.0.0.1:8000/chat") else {
            jarvisResponse = "The local JARVIS address is invalid."
            isThinking = false
            return
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        do {
            request.httpBody = try JSONSerialization.data(
                withJSONObject: ["message": trimmedMessage]
            )
        } catch {
            jarvisResponse = "I could not prepare that request."
            isThinking = false
            return
        }

        URLSession.shared.dataTask(with: request) { data, _, error in
            DispatchQueue.main.async {
                isThinking = false

                if let error {
                    jarvisResponse = "I could not reach the JARVIS brain: \(error.localizedDescription)"
                    return
                }

                guard let data else {
                    jarvisResponse = "The JARVIS brain returned no data."
                    return
                }

                do {
                    let decoded = try JSONDecoder().decode(
                        ChatResponse.self,
                        from: data
                    )
                    jarvisResponse = decoded.response
                    speechManager.speak(decoded.response)
                } catch {
                    jarvisResponse = "I received an unreadable response from the JARVIS brain."
                }
            }
        }.resume()
    }
}

#Preview {
    ContentView()
}
