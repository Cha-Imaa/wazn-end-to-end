export default function QuizOption({
  letter,
  text,
  isSelected,
  isCorrect,
  isWrong,
  isLocked,
  onSelect,
}) {
  return (
    <button
      className={`quiz-option ${isSelected ? "quiz-option--selected" : ""} ${
        isCorrect ? "quiz-option--correct" : ""
      } ${isWrong ? "quiz-option--wrong" : ""}`}
      type="button"
      onClick={onSelect}
      disabled={isLocked}
    >
      <span className="quiz-option-badge">{letter}</span>
      <span className="quiz-option-text">{text}</span>

      {(isSelected || isCorrect) && (
        <span className="quiz-option-check" aria-hidden="true">
          ✓
        </span>
      )}
    </button>
  );
}