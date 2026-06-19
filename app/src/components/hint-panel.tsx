import type { Player, HintType } from "@/lib/types";
import { HINT_ORDER } from "@/lib/types";

function getHintValue(player: Player, type: HintType): string {
  switch (type) {
    case "position":
      return player.position;
    case "years":
      return `${player.first_season}–${player.last_season}`;
    case "college":
      return player.college;
    case "initials":
      return player.initials;
  }
}

interface HintPanelProps {
  player: Player;
  revealedHints: Set<HintType>;
  onReveal: (type: HintType) => void;
  onGiveUp: () => void;
}

export function HintPanel({
  player,
  revealedHints,
  onReveal,
  onGiveUp,
}: HintPanelProps) {
  const allHintsRevealed = HINT_ORDER.every((h) => revealedHints.has(h.type));

  return (
    <div className="space-y-3 w-full max-w-md">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
        Hints
      </h3>
      <div className="grid gap-2">
        {HINT_ORDER.map((hint) => {
          const revealed = revealedHints.has(hint.type);
          return revealed ? (
            <div
              key={hint.type}
              className="flex items-center justify-between px-4 py-2 rounded-md border bg-card border-border"
            >
              <span className="text-sm font-medium text-foreground">
                {hint.label}
              </span>
              <span className="text-sm font-semibold">
                {getHintValue(player, hint.type)}
              </span>
            </div>
          ) : (
            <button
              key={hint.type}
              onClick={() => onReveal(hint.type)}
              className="flex items-center justify-between px-4 py-2 rounded-md border bg-muted/50 border-transparent hover:bg-muted hover:border-border transition-colors cursor-pointer"
            >
              <span className="text-sm font-medium text-muted-foreground">
                {hint.label}
              </span>
              <span className="text-xs text-muted-foreground">Reveal</span>
            </button>
          );
        })}
        {allHintsRevealed && (
          <button
            onClick={onGiveUp}
            className="flex items-center justify-between px-4 py-2 rounded-md border border-destructive/30 bg-destructive/10 hover:bg-destructive/20 transition-colors cursor-pointer mt-1"
          >
            <span className="text-sm font-medium text-destructive">
              Reveal Answer
            </span>
            <span className="text-xs text-destructive/70">Give up</span>
          </button>
        )}
      </div>
    </div>
  );
}
