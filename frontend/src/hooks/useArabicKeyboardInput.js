export function useArabicKeyboardInput({ value, setValue, inputRef, onSubmit }) {
  function insertText(text) {
    const input = inputRef.current;

    if (!input) {
      setValue((current) => current + text);
      return;
    }

    const start = input.selectionStart ?? value.length;
    const end = input.selectionEnd ?? value.length;
    const nextValue = value.slice(0, start) + text + value.slice(end);

    setValue(nextValue);

    requestAnimationFrame(() => {
      input.focus();

      const nextCaret = start + text.length;
      input.setSelectionRange(nextCaret, nextCaret);
    });
  }

  function handleBackspace() {
    const input = inputRef.current;

    if (!input) {
      setValue((current) => current.slice(0, -1));
      return;
    }

    const start = input.selectionStart ?? value.length;
    const end = input.selectionEnd ?? value.length;

    if (start !== end) {
      const nextValue = value.slice(0, start) + value.slice(end);

      setValue(nextValue);

      requestAnimationFrame(() => {
        input.focus();
        input.setSelectionRange(start, start);
      });

      return;
    }

    if (start === 0) {
      return;
    }

    const nextValue = value.slice(0, start - 1) + value.slice(end);

    setValue(nextValue);

    requestAnimationFrame(() => {
      input.focus();
      input.setSelectionRange(start - 1, start - 1);
    });
  }

  return {
    insertText,
    handleBackspace,
    handleSpace: () => insertText(" "),
    handleEnter: onSubmit,
  };
}