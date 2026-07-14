import SwiftUI

struct StatusTimelineView: View {
    let stage: SendStage

    private let steps: [SendStage] = [.searching, .relayFound, .sent, .delivered]

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("Delivery status")
                .font(.caption.weight(.semibold))
                .foregroundStyle(AppTheme.muted)
                .textCase(.uppercase)
                .frame(maxWidth: .infinity, alignment: .center)

            ForEach(steps, id: \.self) { step in
                HStack(spacing: 12) {
                    ZStack {
                        Circle()
                            .fill(reached(step) ? AppTheme.success.opacity(0.18) : AppTheme.card)
                            .frame(width: 28, height: 28)
                        Image(systemName: reached(step) ? "checkmark" : "circle")
                            .font(.caption.weight(.bold))
                            .foregroundStyle(reached(step) ? AppTheme.success : AppTheme.muted)
                    }

                    Text(step.rawValue)
                        .font(.subheadline)
                        .foregroundStyle(reached(step) ? .white : AppTheme.muted)

                    Spacer(minLength: 0)
                }
                .animation(.easeInOut(duration: 0.25), value: stage)
            }
        }
        .offgridCard()
    }

    private func reached(_ step: SendStage) -> Bool {
        let current = steps.firstIndex(of: stage) ?? -1
        let target = steps.firstIndex(of: step) ?? 0
        return target <= current
    }
}
