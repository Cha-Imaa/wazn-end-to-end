function getQuizCompleteResult(score, total) {
  const ratio = total > 0 ? score / total : 0;

  if (ratio === 1) {
    return {
      title: "Perfect bloom",
      message: "Every answer was correct. You understood the root, pattern, and meaning beautifully.",
    };
  }

  if (ratio >= 0.8) {
    return {
      title: "Great progress",
      message: "Only one detail needs review. Look back at the word family, then try again.",
    };
  }

  if (ratio >= 0.6) {
    return {
      title: "Strong growth",
      message: "You are starting to see the pattern. Review the tree once more and keep going.",
    };
  }

  if (ratio >= 0.4) {
    return {
      title: "Good beginning",
      message: "You found some connections. Focus on the root and pattern before trying again.",
    };
  }

  return {
    title: "Keep growing",
    message: "Start with the root, then follow how the pattern changes the meaning.",
  };
}

function getProgressLeaves(score, total) {
  return Array.from({ length: total }, (_, index) =>
    index < score ? "correct" : "empty"
  );
}

export default function QuizComplete({ score, total, onRetry }) {
  const result = getQuizCompleteResult(score, total);
  const progressLeaves = getProgressLeaves(score, total);

  return (
    <section className="quiz-complete" aria-live="polite">
      <div className="quiz-complete-card">
        <img
          className="quiz-complete-leaf"
          src="/assets/decor/leaves-bottom-right.png"
          alt=""
          aria-hidden="true"
        />

        <div className="quiz-complete-icon-wrap" aria-hidden="true">
          <div className="quiz-complete-icon">✓</div>
        </div>

        <p className="quiz-complete-kicker">Quiz finished</p>

        <h3 className="quiz-complete-title">{result.title}</h3>

        <div className="quiz-complete-score-block">
          <span className="quiz-complete-score-label">Your score</span>

          <p className="quiz-complete-score">
            <strong>{score}</strong>
            <span>/</span>
            <span>{total}</span>
          </p>
        </div>

        <div
          className="quiz-complete-progress-leaves"
          aria-label={`You answered ${score} out of ${total} questions correctly`}
        >
          {progressLeaves.map((leafStatus, index) => {
            const src =
              leafStatus === "correct"
                ? "/assets/quiz/quiz-leaf-correct.png"
                : "/assets/quiz/quiz-leaf-empty.png";

            return (
              <img
                key={`quiz-complete-leaf-${index}`}
                className="quiz-complete-progress-leaf"
                src={src}
                alt=""
                aria-hidden="true"
              />
            );
          })}
        </div>

        <p className="quiz-complete-copy">{result.message}</p>

        <button className="quiz-retry-button" type="button" onClick={onRetry}>
          <span className="quiz-retry-button-leaf" aria-hidden="true">
            ✦
          </span>
          <span>Retry quiz</span>
        </button>
      </div>
    </section>
  );
}