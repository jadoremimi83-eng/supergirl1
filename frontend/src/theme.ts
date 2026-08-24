import { Platform } from "react-native";

// SUPER GIRL — Design tokens (Luxe DARK: nero/antracite + champagne/oro + avorio)
export const colors = {
  surface: "#0A0A0A",
  onSurface: "#F4F0E6",
  surfaceSecondary: "#141414",
  onSurfaceSecondary: "#D1CAB8",
  surfaceTertiary: "#1F1E1C",
  onSurfaceTertiary: "#AFA898",
  surfaceInverse: "#F4F0E6",
  onSurfaceInverse: "#0A0A0A",
  brand: "#D4AF37",
  brandPrimary: "#D4AF37",
  onBrandPrimary: "#0A0A0A",
  brandSecondary: "#B68D40",
  brandTertiary: "#2E2412",
  onBrandTertiary: "#EBD399",
  success: "#193325",
  onSuccess: "#7FC99E",
  warning: "#4A3311",
  onWarning: "#DFAF70",
  error: "#47141A",
  onError: "#E07B88",
  info: "#262523",
  onInfo: "#9E9A90",
  border: "#262523",
  borderStrong: "#4A3E22",
  divider: "#1A1918",
};

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  "2xl": 32,
  "3xl": 48,
};

export const radius = {
  sm: 6,
  md: 12,
  lg: 20,
  pill: 999,
};

export const font = {
  display: Platform.select({ ios: "Georgia", android: "serif", default: "Georgia" }),
  displayBold: Platform.select({ ios: "Georgia-Bold", android: "serif", default: "Georgia" }),
};

export const type = { sm: 12, base: 14, lg: 16, xl: 20, "2xl": 24, "3xl": 30 };

// Temperatura lead -> badge semantico (NO emoji nell'UI)
export const TEMP = {
  molto_calda: { label: "Molto Calda", bg: colors.error, fg: colors.onError },
  interessata: { label: "Interessata", bg: colors.warning, fg: colors.onWarning },
  da_coltivare: { label: "Da Coltivare", bg: colors.success, fg: colors.onSuccess },
  non_qualificata: { label: "Non Qualificata", bg: colors.info, fg: colors.onInfo },
} as const;

// Stati pipeline -> etichetta + colore accento
export const STAGES: Record<string, { label: string; short: string; accent: string }> = {
  nuovo_lead: { label: "NUOVO LEAD", short: "Nuovo", accent: "#6C8CBF" },
  ai_conversazione: { label: "AI IN CONVERSAZIONE", short: "AI", accent: "#8E7FD1" },
  in_attesa: { label: "IN ATTESA CLIENTE", short: "In attesa", accent: "#B68D40" },
  interessata: { label: "INTERESSATA", short: "Interessata", accent: "#DFAF70" },
  da_fissare: { label: "DA FISSARE APPUNTAMENTO", short: "Da fissare", accent: "#D4AF37" },
  appuntamento_fissato: { label: "APPUNTAMENTO FISSATO", short: "Fissato", accent: "#7FC99E" },
  non_interessata: { label: "NON INTERESSATA", short: "Non int.", accent: "#9E9A90" },
  persa: { label: "PERSA / NON RISPONDE", short: "Persa", accent: "#7A6F5E" },
};

export function tempOf(key?: string | null) {
  return (key && (TEMP as any)[key]) || TEMP.non_qualificata;
}
export function stageOf(key?: string | null) {
  return (key && STAGES[key]) || STAGES.nuovo_lead;
}
