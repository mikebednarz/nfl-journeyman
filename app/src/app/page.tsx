import { Game } from "@/components/game";

export default function Home() {
  return (
    <>
      <main className="flex-1 flex flex-col items-center justify-start">
        <Game />
      </main>
      <footer className="py-6 px-4 text-center text-xs text-muted-foreground border-t border-border">
        <p>
          Have feedback, suggestions, or found a bug?{" "}
          <a
            href="mailto:feedback@nfljourneyman.com"
            className="underline hover:text-foreground transition-colors"
          >
            feedback@nfljourneyman.com
          </a>
        </p>
      </footer>
    </>
  );
}
