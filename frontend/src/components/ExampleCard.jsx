export default function ExampleCard({
  arabic,
  english,
  imageSrc,
  alt,
  onClick,
}) {
  const CardTag = onClick ? "button" : "article";

  return (
    <CardTag
      className="example-card"
      type={onClick ? "button" : undefined}
      onClick={onClick}
    >
      <img
        className="example-card-icon"
        src={imageSrc}
        alt={alt}
        loading="lazy"
      />

      <p className="example-arabic" dir="rtl">
        {arabic}
      </p>

      <p className="example-english">{english}</p>
    </CardTag>
  );
}