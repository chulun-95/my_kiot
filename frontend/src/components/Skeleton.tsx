interface SkeletonTextProps {
  width?: string;
}

export function SkeletonText({ width = 'w-full' }: SkeletonTextProps) {
  return (
    <div
      data-testid="skeleton-text"
      className={`h-3 ${width} bg-slate-200 rounded animate-pulse`}
    />
  );
}

interface SkeletonRowProps {
  count?: number;
}

export function SkeletonRow({ count = 5 }: SkeletonRowProps) {
  const rows = Array.from({ length: count });
  return (
    <>
      {rows.map((_, i) => (
        <div
          key={i}
          data-testid="skeleton-row"
          className="flex items-center gap-3 py-2"
        >
          <div className="h-3 flex-1 bg-slate-200 rounded animate-pulse" />
          <div className="h-3 w-24 bg-slate-200 rounded animate-pulse" />
          <div className="h-3 w-16 bg-slate-200 rounded animate-pulse" />
        </div>
      ))}
    </>
  );
}

export function SkeletonCard() {
  return (
    <div
      data-testid="skeleton-card"
      className="h-24 w-full bg-slate-200 rounded animate-pulse"
    />
  );
}
