import { BulbIcon } from "./k2-think/icons.jsx";

// Phone-only fixed bottom navigation between the four learning views.
// Hidden on desktop by CSS; desktop keeps the companion panel's own tabs.

function TreeIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        d="M12 3.2c-3.6 0-6.3 2.6-6.3 5.8 0 2.9 2.2 5.2 5.1 5.7V18h2.4v-3.3c2.9-.5 5.1-2.8 5.1-5.7 0-3.2-2.7-5.8-6.3-5.8z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <path
        d="M8.5 21h7M12 18v3"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  );
}

function HomeIcon({ className }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      aria-hidden="true"
      focusable="false"
    >
      <path
        d="M4.5 11.2 12 4.6l7.5 6.6M6.4 10v9.4h11.2V10"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M10.2 19.4v-4.6h3.6v4.6"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default function MobileLearningNav({
  activeView,
  onNavigate,
  onHome,
  quizAvailable = true,
  viewsDisabled = false,
}) {
  const items = [
    {
      id: "tree",
      label: "Tree",
      disabled: false,
      icon: <TreeIcon className="mobile-nav-glyph" />,
    },
    {
      id: "details",
      label: "Details",
      disabled: viewsDisabled,
      icon: (
        <img
          className="mobile-nav-glyph"
          src="/assets/icons/details.svg"
          alt=""
          aria-hidden="true"
        />
      ),
    },
    {
      id: "quiz",
      label: "Quiz",
      disabled: viewsDisabled || !quizAvailable,
      icon: (
        <img
          className="mobile-nav-glyph"
          src="/assets/icons/quiz.svg"
          alt=""
          aria-hidden="true"
        />
      ),
    },
    {
      id: "insights",
      label: "Insights",
      disabled: viewsDisabled,
      icon: <BulbIcon className="mobile-nav-glyph" />,
    },
  ];

  return (
    <nav className="mobile-learning-nav" aria-label="Learning views">
      <button
        type="button"
        className="mobile-nav-item"
        onClick={onHome}
      >
        <HomeIcon className="mobile-nav-glyph" />
        <span className="mobile-nav-label">Home</span>
      </button>
      {items.map((item) => (
        <button
          key={item.id}
          type="button"
          className={`mobile-nav-item ${
            activeView === item.id ? "mobile-nav-item--active" : ""
          }`}
          aria-current={activeView === item.id ? "page" : undefined}
          disabled={item.disabled}
          onClick={() => onNavigate(item.id)}
        >
          {item.icon}
          <span className="mobile-nav-label">{item.label}</span>
        </button>
      ))}
    </nav>
  );
}
