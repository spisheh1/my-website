// Matches the dark dashboard palette exactly
export const C = {
  bg:       '#0d1117',
  surface:  '#161b22',
  surface2: '#21262d',
  border:   '#30363d',
  text:     '#e6edf3',
  text2:    '#8b949e',
  text3:    '#6e7681',
  green:    '#3fb950',
  red:      '#f85149',
  blue:     '#388bfd',
  teal:     '#2ea6da',
  orange:   '#e3b341',
  purple:   '#bc8cff',
};

export const S = {
  // Common layout
  flex1:   { flex: 1 },
  row:     { flexDirection: 'row', alignItems: 'center' },
  center:  { alignItems: 'center', justifyContent: 'center' },
  fill:    { flex: 1, backgroundColor: C.bg },

  // Typography
  h1: { fontSize: 20, fontWeight: '800', color: C.text },
  h2: { fontSize: 16, fontWeight: '700', color: C.text },
  h3: { fontSize: 13, fontWeight: '700', color: C.text },
  h4: { fontSize: 11, fontWeight: '600', color: C.text2, textTransform: 'uppercase', letterSpacing: 0.7 },
  body: { fontSize: 13, color: C.text2, lineHeight: 20 },
  small: { fontSize: 11, color: C.text3 },
  label: { fontSize: 10, color: C.text3, textTransform: 'uppercase', letterSpacing: 0.5 },
  mono:  { fontFamily: 'monospace', fontSize: 12 },

  // Cards
  card: {
    backgroundColor: C.surface,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: C.border,
    padding: 14,
    marginBottom: 10,
  },
  cardFlat: {
    backgroundColor: C.surface,
    borderBottomWidth: 1,
    borderColor: C.border,
    padding: 14,
  },

  // Buttons
  btn: {
    borderRadius: 10,
    paddingVertical: 12,
    paddingHorizontal: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  btnGreen: { backgroundColor: C.green },
  btnRed:   { backgroundColor: C.red },
  btnBlue:  { backgroundColor: C.blue },
  btnGhost: { backgroundColor: C.surface2, borderWidth: 1, borderColor: C.border },

  // Pill/badge
  pill: {
    borderRadius: 20,
    paddingHorizontal: 8,
    paddingVertical: 3,
    alignSelf: 'flex-start',
  },

  // Separator
  sep: { height: 1, backgroundColor: C.border, marginVertical: 8 },
};
