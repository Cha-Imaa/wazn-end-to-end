import { useMemo, useState } from "react";
import QuizOption from "./QuizOption.jsx";
import QuizFeedbackCard from "./QuizFeedbackCard.jsx";
import QuizComplete from "./QuizComplete.jsx";

const OPTION_LETTERS = ["A", "B", "C", "D"];

function shuffleArray(items) {
  const shuffledItems = [...items];

  for (let index = shuffledItems.length - 1; index > 0; index -= 1) {
    const randomIndex = Math.floor(Math.random() * (index + 1));

    [shuffledItems[index], shuffledItems[randomIndex]] = [
      shuffledItems[randomIndex],
      shuffledItems[index],
    ];
  }

  return shuffledItems;
}

export default function WordQuiz({ questions = [] }) {
  const quizQuestions = useMemo(() => {
    return questions.slice(0, 5).map((question) => ({
      ...question,
      shuffledChoices: shuffleArray(question.choices || []),
    }));
  }, [questions]);

  const [questionIndex, setQuestionIndex] = useState(0);
  const [selectedChoiceId, setSelectedChoiceId] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [score, setScore] = useState(0);
  const [isComplete, setIsComplete] = useState(false);
  const [questionResults, setQuestionResults] = useState(
    Array(quizQuestions.length).fill("empty")
  );

  const currentQuestion = quizQuestions[questionIndex];

  if (!quizQuestions.length || !currentQuestion) {
    return null;
  }

  function handleSelect(choiceId) {
    if (submitted) return;
    setSelectedChoiceId(choiceId);
  }

  function handleSubmit() {
    if (!selectedChoiceId || submitted) return;

    const isCorrect = selectedChoiceId === currentQuestion.answer_id;

    if (isCorrect) {
      setScore((currentScore) => currentScore + 1);
    }

    setQuestionResults((currentResults) => {
      const nextResults = [...currentResults];
      nextResults[questionIndex] = isCorrect ? "correct" : "wrong";
      return nextResults;
    });

    setSubmitted(true);
  }

  function handleNext() {
    const isLastQuestion = questionIndex === quizQuestions.length - 1;

    if (isLastQuestion) {
      setIsComplete(true);
      return;
    }

    setQuestionIndex((currentIndex) => currentIndex + 1);
    setSelectedChoiceId("");
    setSubmitted(false);
  }

  function handleRetry() {
    setQuestionIndex(0);
    setSelectedChoiceId("");
    setSubmitted(false);
    setScore(0);
    setIsComplete(false);
    setQuestionResults(Array(quizQuestions.length).fill("empty"));
  }

  const selectedIsCorrect = selectedChoiceId === currentQuestion.answer_id;

  const feedbackStatus = !submitted
    ? null
    : selectedIsCorrect
      ? "correct"
      : "wrong";

  const feedbackExplanation = currentQuestion.explanation;

  if (isComplete) {
    return (
      <section className="word-quiz" aria-label="Mini Quiz">
        <QuizComplete
          score={score}
          total={quizQuestions.length}
          onRetry={handleRetry}
        />
      </section>
    );
  }

  return (
    <section className="word-quiz" aria-label="Mini Quiz">
      <header className="word-quiz-header">
        <img
          className="word-quiz-header-icon"
          src="/assets/decor/footer-learning-page.png"
          alt=""
          aria-hidden="true"
        />

        <h3 className="word-quiz-title">Mini Quiz</h3>

        <div className="word-quiz-leaf-progress" aria-label="Quiz progress">
          {questionResults.map((result, index) => {
            const src =
              result === "correct"
                ? "/assets/quiz/quiz-leaf-correct.png"
                : result === "wrong"
                  ? "/assets/quiz/quiz-leaf-wrong.png"
                  : "/assets/quiz/quiz-leaf-empty.png";

            return (
              <img
                key={`quiz-progress-${index}`}
                className="word-quiz-progress-leaf"
                src={src}
                alt=""
                aria-hidden="true"
              />
            );
          })}
        </div>

        <p className="word-quiz-progress">
          {questionIndex + 1}/{quizQuestions.length}
        </p>
      </header>

      <div className="word-quiz-body">
        <div className="word-quiz-question-column">
          <p className="word-quiz-question">{currentQuestion.question}</p>

          <div className="quiz-options">
            {currentQuestion.shuffledChoices.map((choice, index) => {
              const isSelected = selectedChoiceId === choice.id;
              const isCorrect =
                submitted && choice.id === currentQuestion.answer_id;
              const isWrong =
                submitted &&
                isSelected &&
                choice.id !== currentQuestion.answer_id;

              return (
                <QuizOption
                  key={`${currentQuestion.id}-${choice.id}`}
                  letter={OPTION_LETTERS[index]}
                  text={choice.text}
                  isSelected={isSelected}
                  isCorrect={isCorrect}
                  isWrong={isWrong}
                  isLocked={submitted}
                  onSelect={() => handleSelect(choice.id)}
                />
              );
            })}
          </div>

          <div className="word-quiz-actions">
            {!submitted ? (
              <button
                className="quiz-submit-button"
                type="button"
                onClick={handleSubmit}
                disabled={!selectedChoiceId}
              >
                Submit
              </button>
            ) : (
              <button
                className="quiz-submit-button"
                type="button"
                onClick={handleNext}
              >
                {questionIndex === quizQuestions.length - 1 ? "Finish" : "Next"}
              </button>
            )}
          </div>
        </div>

        <QuizFeedbackCard
          status={feedbackStatus}
          explanation={feedbackExplanation}
        />
      </div>
    </section>
  );
}