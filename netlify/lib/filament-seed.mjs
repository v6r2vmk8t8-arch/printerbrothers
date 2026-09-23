// Startbestand der Filamentfarben. Wird nur verwendet, solange im Admin
// noch nie Filamente gespeichert wurden – danach kommt alles aus dem Netlify-Speicher.
export default [
  { id: "weiss",       name: "Weiß",        hex: "#F2F2EE", translucent: false, available: true },
  { id: "schwarz",     name: "Schwarz",     hex: "#1E1E1E", translucent: false, available: true },
  { id: "gelb",        name: "Gelb",        hex: "#FFD21F", translucent: false, available: true },
  { id: "gruen",       name: "Grün",        hex: "#2FB344", translucent: false, available: true },
  { id: "rot",         name: "Rot",         hex: "#E0262B", translucent: false, available: true },
  { id: "transluzent", name: "Transluzent", hex: "#DCE9EE", translucent: true,  available: true }
];
