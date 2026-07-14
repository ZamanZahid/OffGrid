import SwiftUI
import UIKit

private struct SkyStar {
    let baseX: CGFloat
    let baseY: CGFloat
    let size: CGFloat
    let speed: Double
    let phase: Double
    let orbit: CGFloat
    let twinkle: Double
    let isConstellation: Bool
}

private struct SkyShootingStar {
    let yRatio: CGFloat
    let speed: Double
    let phase: Double
    let length: CGFloat
}

private func skyRandom(_ seed: Int, _ salt: Int) -> CGFloat {
    let value = sin(Double(seed * 127 + salt * 311)) * 10000
    return 0.05 + CGFloat(value - value.rounded(.down)) * 0.9
}

final class NightSkyCanvasView: UIView {
    private var displayLink: CADisplayLink?
    private let backgroundStars: [SkyStar]
    private let constellationStars: [SkyStar]
    private let shootingStars: [SkyShootingStar]

    override init(frame: CGRect) {
        // Sparse background dust — constellations are the main feature.
        backgroundStars = (0..<32).map { i in
            SkyStar(
                baseX: skyRandom(i, 1),
                baseY: skyRandom(i, 2),
                size: 1.5 + skyRandom(i, 3) * 1.5,
                speed: 0.1 + Double(skyRandom(i, 4)) * 0.25,
                phase: Double(skyRandom(i, 5)) * .pi * 2,
                orbit: 5 + skyRandom(i, 6) * 10,
                twinkle: 1.5 + Double(skyRandom(i, 7)) * 2,
                isConstellation: false
            )
        }
        constellationStars = (0..<42).map { i in
            SkyStar(
                baseX: skyRandom(i + 40, 8),
                baseY: skyRandom(i + 40, 9),
                size: 2.5 + skyRandom(i + 40, 10) * 2.5,
                speed: 0.18 + Double(skyRandom(i + 40, 11)) * 0.4,
                phase: Double(skyRandom(i + 40, 12)) * .pi * 2,
                orbit: 12 + skyRandom(i + 40, 13) * 22,
                twinkle: 1 + Double(skyRandom(i + 40, 14)) * 1.5,
                isConstellation: true
            )
        }
        shootingStars = (0..<3).map { i in
            SkyShootingStar(
                yRatio: 0.08 + skyRandom(i + 20, 15) * 0.65,
                speed: 0.14 + Double(skyRandom(i + 20, 16)) * 0.08,
                phase: Double(skyRandom(i + 20, 17)) * 10,
                length: 90 + skyRandom(i + 20, 18) * 110
            )
        }
        super.init(frame: frame)
        isUserInteractionEnabled = false
        isOpaque = true
        backgroundColor = .black
        displayLink = CADisplayLink(target: self, selector: #selector(refresh))
        displayLink?.preferredFrameRateRange = CAFrameRateRange(minimum: 30, maximum: 60, preferred: 30)
        displayLink?.add(to: .main, forMode: .common)
    }

    @available(*, unavailable)
    required init?(coder: NSCoder) { nil }

    deinit {
        displayLink?.invalidate()
    }

    @objc private func refresh() {
        setNeedsDisplay()
    }

    override func draw(_ rect: CGRect) {
        guard let ctx = UIGraphicsGetCurrentContext() else { return }
        let time = CACurrentMediaTime()
        let w = rect.width
        let h = rect.height

        ctx.setFillColor(UIColor.black.cgColor)
        ctx.fill(rect)

        var constellationPoints: [CGPoint] = []

        for star in backgroundStars {
            drawStar(star, time: time, w: w, h: h, ctx: ctx)
        }

        for star in constellationStars {
            let point = drawStar(star, time: time, w: w, h: h, ctx: ctx)
            constellationPoints.append(point)
        }

        drawConstellationLines(points: constellationPoints, w: w, h: h, ctx: ctx)

        for spec in shootingStars {
            drawShootingStar(spec, time: time, w: w, h: h, ctx: ctx)
        }
    }

    @discardableResult
    private func drawStar(_ star: SkyStar, time: Double, w: CGFloat, h: CGFloat, ctx: CGContext) -> CGPoint {
        let angle = time * star.speed + star.phase
        let x = min(max(star.baseX * w + cos(angle) * star.orbit, 3), w - 3)
        let y = min(max(star.baseY * h + sin(angle * 0.85) * star.orbit, 3), h - 3)

        let twinkle = 0.55 + 0.45 * sin(time * star.twinkle + star.phase)
        let alpha = star.isConstellation ? (0.75 + 0.25 * twinkle) : (0.4 + 0.35 * twinkle)

        ctx.setFillColor(UIColor.white.withAlphaComponent(alpha).cgColor)
        ctx.fillEllipse(in: CGRect(x: x - star.size * 0.5, y: y - star.size * 0.5, width: star.size, height: star.size))

        return CGPoint(x: x, y: y)
    }

    private func drawConstellationLines(points: [CGPoint], w: CGFloat, h: CGFloat, ctx: CGContext) {
        let maxDist = min(w, h) * 0.20
        ctx.setLineWidth(1)
        for i in 0..<points.count {
            for j in (i + 1)..<points.count {
                let dx = points[i].x - points[j].x
                let dy = points[i].y - points[j].y
                let dist = hypot(dx, dy)
                guard dist < maxDist else { continue }
                let alpha = (1 - dist / maxDist) * 0.45
                ctx.setStrokeColor(UIColor.white.withAlphaComponent(alpha).cgColor)
                ctx.move(to: points[i])
                ctx.addLine(to: points[j])
                ctx.strokePath()
            }
        }
    }

    private func drawShootingStar(_ spec: SkyShootingStar, time: Double, w: CGFloat, h: CGFloat, ctx: CGContext) {
        let cycle = 9.0 / spec.speed
        let progress = (time + spec.phase).truncatingRemainder(dividingBy: cycle)
        guard progress < 1.1 else { return }

        let t = progress / 1.1
        let headX = w * (1.08 - t * 1.25)
        let headY = h * spec.yRatio
        let tailX = headX + spec.length
        let tailY = headY + spec.length * 0.28
        let fade = 1 - t

        ctx.setLineWidth(1.5)
        ctx.setStrokeColor(UIColor.white.withAlphaComponent(0.75 * fade).cgColor)
        ctx.move(to: CGPoint(x: tailX, y: tailY))
        ctx.addLine(to: CGPoint(x: headX, y: headY))
        ctx.strokePath()
    }
}

struct ConstellationBackground: View {
    var body: some View {
        NightSkyRepresentable()
            .ignoresSafeArea()
    }
}

private struct NightSkyRepresentable: UIViewRepresentable {
    func makeUIView(context: Context) -> NightSkyCanvasView {
        let view = NightSkyCanvasView()
        view.contentMode = .scaleToFill
        return view
    }

    func updateUIView(_ uiView: NightSkyCanvasView, context: Context) {}
}

extension View {
    func offgridNightSkyBackground() -> some View {
        background {
            ConstellationBackground()
        }
    }
}
