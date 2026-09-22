// Startbestand des Shops. Wird nur verwendet, solange im Admin noch nie
// gespeichert wurde – danach kommt alles aus dem Netlify-Speicher.
export default [
  { id: "drache",     name: "Mini-Drache",        price: 8,    icon: "drache",  image: null, visible: true, desc: "Schlüsselanhänger mit beweglichen Gelenken, ohne Montage gedruckt." },
  { id: "vase",       name: "Turm-Vase",          price: 16,   icon: "vase",    image: null, visible: true, desc: "Im Vasenmodus gedruckt, eine einzige Außenwand, wasserdicht." },
  { id: "schach",     name: "Schachkönig",        price: 6.5,  icon: "schach",  image: null, visible: true, desc: "Einzelne Figur aus unserem selbst entworfenen Schachset." },
  { id: "spinner",    name: "Fidget-Spinner",     price: 14,   icon: null, image: "/images/fidget-spinner.jpg",   visible: true, desc: "Frei drehbarer Drei-Blatt-Rotor mit Kugellager." },
  { id: "stand",      name: "Handy-Ständer",      price: 11,   icon: "stand",   image: null, visible: true, desc: "Verstellbarer Winkel, stabiler Stand – unser meistgedrucktes Teil." },
  { id: "flitzer",    name: "Renn-Flitzer",       price: 9,    icon: "flitzer", image: null, visible: true, desc: "Rollende Räder, direkt mitgedruckt, kein Zusammenbau nötig." },
  { id: "panfloete",  name: "Panflöte",           price: 19,   icon: null, image: "/images/panfloete.jpg",        visible: true, desc: "Acht Röhren in einem Stück gedruckt, mit graviertem Muster – spielbar." },
  { id: "spinner2",   name: "Shuriken-Spinner",   price: 13,   icon: null, image: "/images/fidget-spinner-2.jpg", visible: true, desc: "Vierarmige Wurfstern-Form mit Kugellager im Zentrum." },
  { id: "spinner3",   name: "Zahnkappen-Spinner", price: 15,   icon: null, image: "/images/fidget-spinner-3.jpg", visible: true, desc: "Drei schlanke Arme mit gezahnten Kappen und Kugellagern an den Enden." },
  { id: "wurfstern2", name: "Wurfstern Fünf",     price: 7.5,  icon: null, image: "/images/wurfstern-2.jpg",      visible: true, desc: "Fünfarmige Variante unseres Wurfsterns, in leuchtendem Gelb." }
];
