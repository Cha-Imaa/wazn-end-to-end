export const TREE_ENTRANCE_ANIMATION = {
  // Slack after the computed finish time before the entering state ends,
  // so the class swap never lands while the last leaf is still painting.
  totalDurationBuffer: 150,

  ground: {
    delay: 0,
    duration: 420,
  },

  trunk: {
    delay: 220,
    duration: 760,
  },

  rootText: {
    delay: 720,
    duration: 420,
  },

  branches: {
    delay: 850,
    duration: 500,
  },

  smallLeaves: {
    delay: 1220,
    duration: 340,
    stagger: 45,
  },

  bigLeaves: {
    delayAfterSmallLeaves: 180,
    duration: 560,
    stagger: 95,
  },
};

export const BIG_LEAF_COUNT = 8;