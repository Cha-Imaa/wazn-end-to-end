export default function LogoButton({ onClick }) {
  function handleClick(event) {
    if (onClick) {
      event.preventDefault();
      onClick();
    }
  }

  return (
    <a
      className="brand-mark"
      href="/"
      aria-label="Wazn home"
      onClick={handleClick}
    >
      <img
        className="brand-logo"
        src="/assets/logo/wazn-logo.png"
        alt="Wazn"
      />
    </a>
  );
}