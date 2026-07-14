export const quizzes = {
  مدرسة: [
    {
      id: "school-meaning",
      prompt: "What does مَدْرَسَة mean?",
      options: ["school", "teacher", "lesson", "library"],
      correctAnswer: "school",
      correctExplanation: "Correct. مَدْرَسَة is a place where studying happens.",
      wrongExplanation:
        "Not quite. مَدْرَسَة means school — a place where studying happens.",
    },
    {
      id: "school-root",
      prompt: "What is the root of مَدْرَسَة?",
      options: ["د ر س", "ك ت ب", "ف ت ح", "ت ج ر"],
      correctAnswer: "د ر س",
      correctExplanation:
        "Correct. The root د ر س carries the idea of studying and learning.",
      wrongExplanation:
        "Not quite. The root of مَدْرَسَة is د ر س, connected to studying.",
    },
    {
      id: "school-pattern",
      prompt: "Which pattern does مَدْرَسَة follow?",
      options: ["مَفْعَلَة", "فَاعِل", "مِفْعَال", "فِعَالَة"],
      correctAnswer: "مَفْعَلَة",
      correctExplanation:
        "Correct. مَفْعَلَة often forms a place where the root action happens.",
      wrongExplanation:
        "Not quite. مَدْرَسَة follows the pattern مَفْعَلَة.",
    },
    {
      id: "teacher-meaning",
      prompt: "What does مُدَرِّس mean?",
      options: ["teacher", "student", "lesson", "studied"],
      correctAnswer: "teacher",
      correctExplanation:
        "Correct. مُدَرِّس means teacher — someone who teaches.",
      wrongExplanation: "Not quite. مُدَرِّس means teacher.",
    },
    {
      id: "lesson-meaning",
      prompt: "Which word means lesson?",
      options: ["دَرْس", "دَارِس", "تَدْرِيس", "دُرُوس"],
      correctAnswer: "دَرْس",
      correctExplanation: "Correct. دَرْس means lesson.",
      wrongExplanation: "Not quite. دَرْس means lesson.",
    },
  ],

  مكتبة: [
    {
      id: "library-meaning",
      prompt: "What does مَكْتَبَة mean?",
      options: ["library", "writer", "book", "school"],
      correctAnswer: "library",
      correctExplanation:
        "Correct. مَكْتَبَة means library — a place connected to books and writing.",
      wrongExplanation: "Not quite. مَكْتَبَة means library.",
    },
    {
      id: "library-root",
      prompt: "What is the root of مَكْتَبَة?",
      options: ["ك ت ب", "د ر س", "ف ت ح", "ت ج ر"],
      correctAnswer: "ك ت ب",
      correctExplanation:
        "Correct. The root ك ت ب carries the idea of writing and books.",
      wrongExplanation: "Not quite. The root of مَكْتَبَة is ك ت ب.",
    },
    {
      id: "library-pattern",
      prompt: "Which pattern does مَكْتَبَة follow?",
      options: ["مَفْعَلَة", "فَاعِل", "فِعَالَة", "مَفْعُول"],
      correctAnswer: "مَفْعَلَة",
      correctExplanation:
        "Correct. مَفْعَلَة often forms a place connected to the root action.",
      wrongExplanation:
        "Not quite. مَكْتَبَة follows the pattern مَفْعَلَة.",
    },
    {
      id: "writer-meaning",
      prompt: "What does كَاتِب mean?",
      options: ["writer", "book", "library", "written"],
      correctAnswer: "writer",
      correctExplanation: "Correct. كَاتِب means writer — a person who writes.",
      wrongExplanation: "Not quite. كَاتِب means writer.",
    },
    {
      id: "book-meaning",
      prompt: "Which word means book?",
      options: ["كِتَاب", "كُتُب", "مَكْتَب", "مَكْتُوب"],
      correctAnswer: "كِتَاب",
      correctExplanation: "Correct. كِتَاب means book.",
      wrongExplanation: "Not quite. كِتَاب means book.",
    },
  ],

  مفتاح: [
    {
      id: "key-meaning",
      prompt: "What does مِفْتَاح mean?",
      options: ["key", "door", "book", "trade"],
      correctAnswer: "key",
      correctExplanation:
        "Correct. مِفْتَاح means key — something used for opening.",
      wrongExplanation: "Not quite. مِفْتَاح means key.",
    },
    {
      id: "key-root",
      prompt: "What is the root of مِفْتَاح?",
      options: ["ف ت ح", "ك ت ب", "د ر س", "ت ج ر"],
      correctAnswer: "ف ت ح",
      correctExplanation:
        "Correct. The root ف ت ح carries the idea of opening.",
      wrongExplanation: "Not quite. The root of مِفْتَاح is ف ت ح.",
    },
    {
      id: "key-pattern",
      prompt: "Which pattern does مِفْتَاح follow?",
      options: ["مِفْعَال", "مَفْعَلَة", "فَاعِل", "فِعَالَة"],
      correctAnswer: "مِفْعَال",
      correctExplanation:
        "Correct. مِفْعَال can form a tool or object connected to the root action.",
      wrongExplanation:
        "Not quite. مِفْتَاح follows the pattern مِفْعَال.",
    },
    {
      id: "open-meaning",
      prompt: "What does مَفْتُوح mean?",
      options: ["open / opened", "key", "opener", "opening"],
      correctAnswer: "open / opened",
      correctExplanation: "Correct. مَفْتُوح means open or opened.",
      wrongExplanation: "Not quite. مَفْتُوح means open or opened.",
    },
    {
      id: "opener-meaning",
      prompt: "Which word means opener?",
      options: ["فَاتِح", "فَتْحَة", "مِفْتَاح", "اِفْتِتَاح"],
      correctAnswer: "فَاتِح",
      correctExplanation:
        "Correct. فَاتِح means opener — someone or something that opens.",
      wrongExplanation:
        "Not quite. فَاتِح means opener or one who opens.",
    },
  ],

  تجارة: [
    {
      id: "trade-meaning",
      prompt: "What does تِجَارَة mean?",
      options: ["trade", "merchant", "store / shop", "school"],
      correctAnswer: "trade",
      correctExplanation: "Correct. تِجَارَة means trade or commerce.",
      wrongExplanation: "Not quite. تِجَارَة means trade or commerce.",
    },
    {
      id: "trade-root",
      prompt: "What is the root of تِجَارَة?",
      options: ["ت ج ر", "د ر س", "ك ت ب", "ف ت ح"],
      correctAnswer: "ت ج ر",
      correctExplanation:
        "Correct. The root ت ج ر carries the idea of trade and commerce.",
      wrongExplanation: "Not quite. The root of تِجَارَة is ت ج ر.",
    },
    {
      id: "trade-pattern",
      prompt: "Which pattern does تِجَارَة follow?",
      options: ["فِعَالَة", "مَفْعَلَة", "فَاعِل", "مِفْعَال"],
      correctAnswer: "فِعَالَة",
      correctExplanation:
        "Correct. فِعَالَة can form a verbal noun naming an action, practice, or field.",
      wrongExplanation:
        "Not quite. تِجَارَة follows the pattern فِعَالَة.",
    },
    {
      id: "merchant-meaning",
      prompt: "What does تَاجِر mean?",
      options: ["merchant", "trade", "store / shop", "commercial"],
      correctAnswer: "merchant",
      correctExplanation:
        "Correct. تَاجِر means merchant — a person who trades.",
      wrongExplanation: "Not quite. تَاجِر means merchant.",
    },
    {
      id: "store-meaning",
      prompt: "What does مَتْجَر mean?",
      options: ["store / shop", "merchant", "trade", "commercial"],
      correctAnswer: "store / shop",
      correctExplanation:
        "Correct. مَتْجَر means store or shop — a place where trade happens.",
      wrongExplanation: "Not quite. مَتْجَر means store or shop.",
    },
  ],
};