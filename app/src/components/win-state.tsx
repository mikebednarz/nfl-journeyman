import type { Player } from "@/lib/types";
import { FranchisePath } from "./franchise-path";

interface WinStateProps {
  player: Player;
  guessCount: number;
  hintsUsed: number;
  gaveUp?: boolean;
}

export function WinState({ player, guessCount, hintsUsed, gaveUp }: WinStateProps) {
  return (
    <div className="text-center space-y-6 animate-in fade-in duration-500">
      <p className={`text-lg font-semibold ${gaveUp ? "text-muted-foreground" : "text-green-400"}`}>
        {gaveUp ? "Answer Revealed" : "Correct!"}
      </p>
      <div className="space-y-2">
        <h2 className="text-3xl font-bold">{player.full_name}</h2>
        <p className="text-muted-foreground">
          {player.position} · {player.first_season}–{player.last_season} ·{" "}
          {player.college}
        </p>
      </div>
      <FranchisePath franchises={player.franchises} />
      <div className="flex gap-6 justify-center text-sm text-muted-foreground">
        <span>
          {guessCount} {guessCount === 1 ? "guess" : "guesses"}
        </span>
        <span>
          {hintsUsed} {hintsUsed === 1 ? "hint" : "hints"} used
        </span>
      </div>
    </div>
  );
}
