// The game's colours for tiers and elements, as wynncard.tooltip uses them; here they only mark chips.

export const TIER_COLOURS: Readonly<Record<string, string>> = {
  normal: '#ffffff',
  unique: '#ffff55',
  rare: '#ff55ff',
  set: '#55ff55',
  legendary: '#55ffff',
  fabled: '#ff5555',
  mythic: '#aa00aa',
};

export const ELEMENT_COLOURS: Readonly<Record<string, string>> = {
  neutral: '#ffaa00',
  earth: '#00aa00',
  thunder: '#ffff55',
  water: '#55ffff',
  fire: '#ff5555',
  air: '#ffffff',
};
