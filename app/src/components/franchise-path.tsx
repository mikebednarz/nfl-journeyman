import type { Franchise } from "@/lib/types";

export function FranchisePath({ franchises }: { franchises: Franchise[] }) {
  return (
    <div className="flex flex-wrap items-center gap-x-2 gap-y-1.5 justify-center px-2">
      {franchises.map((f, i) => (
        <span key={i} className="flex items-center gap-2">
          <span className="bg-primary text-primary-foreground px-2.5 py-1 sm:px-3 sm:py-1.5 rounded-md text-xs sm:text-sm font-semibold whitespace-nowrap">
            {f.display}
          </span>
          {i < franchises.length - 1 && (
            <span className="text-muted-foreground text-base sm:text-lg">→</span>
          )}
        </span>
      ))}
    </div>
  );
}
