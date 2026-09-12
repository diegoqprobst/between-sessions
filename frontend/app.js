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
function setListening(on) { voiceButton.setAttribute("aria-pressed", String(on)); companion.classList.toggle("listening", on); voiceTitle.textContent = on ? "Te escucho" : "Habla con Nubo"; voiceCopy.textContent = on ? "Suelta cuando termines." : "Mantén pulsado para contarle cómo vas."; if (!on) notify("Tu reflexión queda privada hasta que decidas compartirla."); }
voiceButton.addEventListener("pointerdown", () => setListening(true)); voiceButton.addEventListener("pointerup", () => setListening(false)); voiceButton.addEventListener("pointerleave", () => { if (voiceButton.getAttribute("aria-pressed") === "true") setListening(false); }); voiceButton.addEventListener("keydown", (event) => { if (event.key === " " || event.key === "Enter") setListening(true); }); voiceButton.addEventListener("keyup", (event) => { if (event.key === " " || event.key === "Enter") setListening(false); });
document.querySelector("#text-button").addEventListener("click", () => notify("Abriremos el chat privado para escribirle a Nubo."));
document.querySelectorAll(".nav-item").forEach((item) => item.addEventListener("click", () => { document.querySelectorAll(".nav-item").forEach((button) => button.classList.remove("active")); item.classList.add("active"); if (item.textContent !== "Hoy") notify(`${item.textContent}: próxima pantalla en construcción.`); }));
