// Tiny server-renderable SVG charts. No client JS, no charting library.
// Works in `output: 'export'` and renders identically on first paint.

import { fmtUSD } from "@/lib/recipients";

type HBarItem = { label: string; value: number; href?: string };

export function HBar({
  items,
  max,
  height = 22,
  labelWidth = 280,
  width = 600,
  formatter = (v: number) => fmtUSD(v),
}: {
  items: HBarItem[];
  max?: number;
  height?: number;
  labelWidth?: number;
  width?: number;
  formatter?: (v: number) => string;
}) {
  if (items.length === 0) return <p>(no data)</p>;
  const m = max ?? Math.max(...items.map((i) => i.value), 1);
  const barWidth = Math.max(width - labelWidth - 120, 100);
  const rowH = height + 8;
  const totalH = rowH * items.length;
  return (
    <svg
      role="img"
      width="100%"
      viewBox={`0 0 ${width} ${totalH}`}
      preserveAspectRatio="xMinYMin meet"
      style={{ maxWidth: width, display: "block" }}
    >
      {items.map((it, i) => {
        const y = i * rowH;
        const w = Math.max((it.value / m) * barWidth, 1);
        const label = it.label.length > 42 ? it.label.slice(0, 41) + "…" : it.label;
        return (
          <g key={it.label + i} transform={`translate(0, ${y})`}>
            <text x={0} y={height - 6} fontSize={12} fill="#1c1917">
              {it.href ? (
                <a href={it.href} style={{ textDecoration: "underline" }}>
                  {label}
                </a>
              ) : (
                label
              )}
            </text>
            <rect
              x={labelWidth}
              y={2}
              height={height - 4}
              width={w}
              fill="#0f766e"
              rx={2}
            />
            <text
              x={labelWidth + w + 6}
              y={height - 6}
              fontSize={12}
              fill="#44403c"
            >
              {formatter(it.value)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

export function VBar({
  items,
  height = 200,
  width = 600,
  formatter = (v: number) => fmtUSD(v),
}: {
  items: { label: string; value: number }[];
  height?: number;
  width?: number;
  formatter?: (v: number) => string;
}) {
  if (items.length === 0) return <p>(no data)</p>;
  const max = Math.max(...items.map((i) => i.value), 1);
  const padX = 40;
  const padTop = 16;
  const padBottom = 36;
  const innerW = width - padX * 2;
  const innerH = height - padTop - padBottom;
  const barW = Math.max((innerW / items.length) - 8, 8);
  return (
    <svg
      role="img"
      width="100%"
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="xMinYMin meet"
      style={{ maxWidth: width, display: "block" }}
    >
      {/* Y-axis baseline */}
      <line
        x1={padX}
        x2={width - padX}
        y1={padTop + innerH}
        y2={padTop + innerH}
        stroke="#d6d3d1"
      />
      {items.map((it, i) => {
        const x = padX + i * (innerW / items.length) + (innerW / items.length - barW) / 2;
        const h = (it.value / max) * innerH;
        const y = padTop + innerH - h;
        return (
          <g key={it.label + i}>
            <rect x={x} y={y} width={barW} height={h} fill="#0f766e" rx={2} />
            <text
              x={x + barW / 2}
              y={padTop + innerH + 16}
              fontSize={12}
              fill="#1c1917"
              textAnchor="middle"
            >
              {it.label}
            </text>
            <title>{`${it.label}: ${formatter(it.value)}`}</title>
            {/* value label above bar if there's space */}
            {h > 24 ? (
              <text
                x={x + barW / 2}
                y={y - 4}
                fontSize={10}
                fill="#44403c"
                textAnchor="middle"
              >
                {formatter(it.value)}
              </text>
            ) : null}
          </g>
        );
      })}
    </svg>
  );
}

export function MetricCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div
      style={{
        border: "1px solid #e7e5e4",
        borderRadius: 8,
        padding: "12px 16px",
        background: "white",
        minWidth: 160,
      }}
    >
      <div style={{ fontSize: "0.85rem", color: "#78716c", marginBottom: 4 }}>
        {label}
      </div>
      <div style={{ fontSize: "1.6rem", fontWeight: 700, lineHeight: 1.1 }}>
        {value}
      </div>
      {hint ? (
        <div style={{ fontSize: "0.75rem", color: "#78716c", marginTop: 4 }}>
          {hint}
        </div>
      ) : null}
    </div>
  );
}

export function MetricGrid({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
        gap: 12,
        margin: "1.5rem 0",
      }}
    >
      {children}
    </div>
  );
}
