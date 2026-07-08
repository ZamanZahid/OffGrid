import SwiftUI

/// Vertical checklist that fills in as the message travels. This little
/// animation is the demo's "wow" — an offline phone reaching "Delivered ✓".
struct StatusTimelineView: View {
    let stage: SendStage

    private let steps: [SendStage] = [.searching, .relayFound, .sent, .delivered]

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            ForEach(steps, id: \.self) { step in
                HStack(spacing: 12) {
                    Image(systemName: reached(step) ? "checkmark.circle.fill" : "circle")
                        .foregroundStyle(reached(step) ? .green : .secondary)
                        .imageScale(.large)
                    Text(step.rawValue)
                        .foregroundStyle(reached(step) ? .primary : .secondary)
                    Spacer()
                }
                .animation(.easeInOut, value: stage)
            }
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.quaternary.opacity(0.4))
        .clipShape(RoundedRectangle(cornerRadius: 14))
    }

    private func reached(_ step: SendStage) -> Bool {
        let current = steps.firstIndex(of: stage) ?? -1
        let target = steps.firstIndex(of: step) ?? 0
        return target <= current
    }
}
