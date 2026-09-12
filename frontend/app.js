const toast = document.querySelector("#toast");
const companion = document.querySelector("#companion");
const message = document.querySelector("#message");
const voiceButton = document.querySelector("#voice-button");
const voiceTitle = document.querySelector("#voice-title");
const voiceCopy = document.querySelector("#voice-copy");
const questButton = document.querySelector("#accept-quest");
let questStarted = false;
function notify(text) { toast.textContent = text; toast.classList.add("visible"); setTimeout(() => toast.classList.remove("visible"), 3200); }
questButton.addEventListener("click", () => { questStarted = !questStarted; questButton.textContent = questStarted ? "Llevo 5 minutos" : "Voy a intentarlo"; document.querySelector("#progress-fill").style.width = questStarted ? "50%" : "0"; document.querySelector("#quest-count").textContent = questStarted ? "5 / 10 min" : "0 / 10 min"; companion.classList.toggle("celebrate", questStarted); notify(questStarted ? "Bien. Sin prisa: cinco minutos también cuentan." : "Reto reiniciado."); });
document.querySelector("#choose-another").addEventListener("click", () => { message.textContent = "Otra opción: manda un mensaje breve a alguien que te haga bien. ¿Te acompaño a elegir a quién?"; notify("Nubo preparó un reto de conexión."); });
const careDone = new Set();
document.querySelectorAll(".care-action").forEach((button) => button.addEventListener("click", () => {
  const ritual = button.dataset.care;
  if (careDone.has(ritual)) return;
  careDone.add(ritual); button.classList.add("done");
  document.querySelector("#care-count").textContent = `${careDone.size} / 3`;
  document.querySelector("#care-fill").style.width = `${careDone.size * 33.33}%`;
  if (ritual === "agua") { companion.classList.add("hydrated"); message.textContent = "Gracias por registrar ese cuidado. Nubo se siente más fresco contigo."; }
  if (ritual === "movimiento") companion.classList.add("celebrate");
  notify("Ritual registrado para ti. No se comparte con tu empleador.");
}));
function setListening(on) { voiceButton.setAttribute("aria-pressed", String(on)); companion.classList.toggle("listening", on); voiceTitle.textContent = on ? "Te escucho" : "Habla con Nubo"; voiceCopy.textContent = on ? "Suelta cuando termines." : "Mantén pulsado para contarle cómo vas."; if (!on) notify("Tu reflexión queda privada hasta que decidas compartirla."); }
voiceButton.addEventListener("pointerdown", () => setListening(true)); voiceButton.addEventListener("pointerup", () => setListening(false)); voiceButton.addEventListener("pointerleave", () => { if (voiceButton.getAttribute("aria-pressed") === "true") setListening(false); }); voiceButton.addEventListener("keydown", (event) => { if (event.key === " " || event.key === "Enter") setListening(true); }); voiceButton.addEventListener("keyup", (event) => { if (event.key === " " || event.key === "Enter") setListening(false); });
document.querySelector("#text-button").addEventListener("click", () => notify("Abriremos el chat privado para escribirle a Nubo."));
const journalSheet = document.querySelector("#journal-sheet");
const showJournal = (show) => { journalSheet.hidden = !show; if (show) document.querySelector("#journal-note").focus(); };
document.querySelector("#close-journal").addEventListener("click", () => showJournal(false));
let selectedMood = "";
document.querySelectorAll("[data-mood]").forEach((button) => button.addEventListener("click", () => { document.querySelectorAll("[data-mood]").forEach((item) => item.setAttribute("aria-pressed", "false")); button.setAttribute("aria-pressed", "true"); selectedMood = button.dataset.mood; }));
document.querySelector("#save-journal").addEventListener("click", () => { const note = document.querySelector("#journal-note").value.trim(); if (!note) return notify("Escribe una línea para guardar tu entrada."); document.querySelector("#entry-mood").textContent = selectedMood ? `Ahora me siento: ${selectedMood}` : "Entrada privada"; document.querySelector("#entry-note").textContent = note; document.querySelector("#journal-entry").hidden = false; notify("Guardado en esta pantalla de demo. No se envió a nadie."); });
document.querySelectorAll(".nav-item").forEach((item) => item.addEventListener("click", () => { document.querySelectorAll(".nav-item").forEach((button) => button.classList.remove("active")); item.classList.add("active"); if (item.textContent === "Diario") return showJournal(true); if (item.textContent === "Hoy") return showJournal(false); notify(`${item.textContent}: próxima pantalla en construcción.`); }));
