// Visual identity of each merit tier. Keys match TeacherMeritScore.tier on the server.
export const TIERS = {
  laureate:      { name: 'Aeterna Laureate',      metal: 'Gold',     light: '#f8e7a8', mid: '#d4a937', dark: '#8a6414', ink: '#4a3408' },
  distinguished: { name: 'Distinguished Scholar', metal: 'Silver',   light: '#f1f3f5', mid: '#aeb7c0', dark: '#6b7682', ink: '#2f3740' },
  fellow:        { name: 'Merit Fellow',          metal: 'Bronze',   light: '#f0cfa8', mid: '#c0824a', dark: '#7a4719', ink: '#4a2a0c' },
  associate:     { name: 'Associate Educator',    metal: 'Standard', light: '#cfe0e2', mid: '#5d7c80', dark: '#1f3a3f', ink: '#ffffff' },
  emerging:      { name: 'Emerging Educator',     metal: 'Emerging', light: '#ece6d6', mid: '#c9bfa5', dark: '#8c8268', ink: '#3b3623' },
}
export const tierOf = (key) => TIERS[key] || TIERS.emerging
export const metalGradient = (t) => `linear-gradient(135deg, ${t.light} 0%, ${t.mid} 45%, ${t.dark} 100%)`
export const TIER_FLOORS = [['emerging', 0], ['associate', 60], ['fellow', 70], ['distinguished', 80], ['laureate', 90]]
