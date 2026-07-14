import DecorativeLeaves from "./DecorativeLeaves.jsx";
import K2Badge from "./K2Badge.jsx";

export default function AppShell({
  keyboardOpen,
  onLogoClick,
  variant = "landing",
  children,
}) {
  const isLanding = variant === "landing";

  return (
    <main className="page">
      <section
        className={`app-shell ${
          keyboardOpen ? "keyboard-open" : "keyboard-closed"
        } ${isLanding ? "app-shell-landing" : "app-shell-learning"}`}
        aria-label="Wazn Arabic root and pattern learning app"
      >
        {isLanding && <DecorativeLeaves />}

        {children}

        {isLanding && <K2Badge />}
      </section>
    </main>
  );
}