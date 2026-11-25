// Startbestand der Filamentfarben. Wird nur verwendet, solange im Admin
// noch nie Filamente gespeichert wurden – danach kommt alles aus dem Netlify-Speicher.
export default [
  { id: "weiss",       name: "Weiß",        hex: "#F2F2EE", material: "PLA", translucent: false, available: true },
  { id: "schwarz",     name: "Schwarz",     hex: "#1E1E1E", material: "PLA", translucent: false, available: true },
  { id: "gelb",        name: "Gelb",        hex: "#FFD21F", material: "PLA", translucent: false, available: true },
  { id: "gruen",       name: "Grün",        hex: "#2FB344", material: "PLA", translucent: false, available: true },
  { id: "rot",         name: "Rot",         hex: "#E0262B", material: "PLA", translucent: false, available: true },
  { id: "transluzent", name: "Transluzent", hex: "#DCE9EE", material: "PLA", translucent: true,  available: true }
];
