export default function QuizFeedbackCard({ status, explanation }) {
  const isCorrect = status === "correct";
  const isWrong = status === "wrong";

  return (
    <aside
      className={`quiz-feedback-card ${
        isCorrect ? "quiz-feedback-card--correct" : ""
      } ${isWrong ? "quiz-feedback-card--wrong" : ""}`}
    >
      <img
        className="quiz-feedback-watermark"
        src="/assets/decor/leaves-bottom-right.png"
        alt=""
        aria-hidden="true"
      />

      {!status && (
        <>
          <div className="quiz-feedback-icon quiz-feedback-icon--neutral">?</div>
          <h4 className="quiz-feedback-title">Choose an answer.</h4>
          <p className="quiz-feedback-copy">
            Select one option, then submit to check it.
          </p>
        </>
      )}

      {isCorrect && (
        <>
          <img
            className="quiz-feedback-status-image quiz-feedback-status-image--correct"
            src="/assets/quiz/quiz-leaf-correct-icon.png"
            alt=""
            aria-hidden="true"
          />
          <h4 className="quiz-feedback-title">Correct!</h4>
          <p className="quiz-feedback-copy">{explanation}</p>
        </>
      )}

      {isWrong && (
        <>
          <img
            className="quiz-feedback-status-image quiz-feedback-status-image--wrong"
            src="/assets/quiz/quiz-leaf-wrong-icon.png"
            alt=""
            aria-hidden="true"
          />
          <h4 className="quiz-feedback-title">Not quite</h4>
          <p className="quiz-feedback-copy">{explanation}</p>
        </>
      )}
    </aside>
  );
}