/**
 * Inline SVG string for the bodice front pattern piece.
 * This is a simplified geometric approximation with named element IDs
 * matching the SAMPLE_CASCADE_SCRIPT element references.
 *
 * Element IDs:
 *   - bodice-front-piece: main bodice piece (neckline to waist)
 *   - bust-dart: dart triangle on the side seam
 *   - side-seam-line: the right side seam (used for "truing")
 */
export const BODICE_FRONT_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 400" width="300" height="400">
  <g id="bodice-front-piece">
    <path d="M 75,30 Q 100,20 150,18 Q 200,20 225,30" fill="none" stroke="#2d2d2d" stroke-width="2"/>
    <line x1="75" y1="30" x2="30" y2="80" stroke="#2d2d2d" stroke-width="2"/>
    <line x1="225" y1="30" x2="270" y2="80" stroke="#2d2d2d" stroke-width="2"/>
    <path d="M 30,80 Q 20,130 40,160" fill="none" stroke="#2d2d2d" stroke-width="2"/>
    <path d="M 270,80 Q 280,130 260,160" fill="none" stroke="#2d2d2d" stroke-width="2"/>
    <line x1="40" y1="160" x2="35" y2="230" stroke="#2d2d2d" stroke-width="2"/>
    <line x1="35" y1="240" x2="38" y2="370" stroke="#2d2d2d" stroke-width="2"/>
    <line x1="260" y1="160" x2="262" y2="370" stroke="#2d2d2d" stroke-width="2"/>
    <line x1="38" y1="370" x2="262" y2="370" stroke="#2d2d2d" stroke-width="2"/>
    <line x1="150" y1="50" x2="150" y2="360" stroke="#888" stroke-width="1" stroke-dasharray="6,4"/>
    <polygon points="150,45 145,58 155,58" fill="#888"/>
    <polygon points="150,365 145,352 155,352" fill="#888"/>
    <text x="158" y="210" font-family="sans-serif" font-size="10" fill="#888" transform="rotate(90, 158, 210)">CF</text>
  </g>
  <g id="bust-dart">
    <line x1="35" y1="230" x2="110" y2="210" stroke="#2d2d2d" stroke-width="2"/>
    <line x1="35" y1="240" x2="110" y2="210" stroke="#2d2d2d" stroke-width="2"/>
    <circle cx="110" cy="210" r="3" fill="#2d2d2d" opacity="0.5"/>
  </g>
  <g id="side-seam-line">
    <line x1="262" y1="160" x2="262" y2="370" stroke="#c0392b" stroke-width="2.5" stroke-dasharray="8,4"/>
    <text x="272" y="270" font-family="sans-serif" font-size="9" fill="#c0392b" transform="rotate(90, 272, 270)">Side Seam</text>
  </g>
</svg>`;
