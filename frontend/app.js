const toast = document.querySelector("#toast");
const notify = (message) => {
  toast.textContent = message;
  toast.classList.add("visible");
  window.setTimeout(() => toast.classList.remove("visible"), 3200);
};

document.querySelector("#pause-button").addEventListener("click", (event) => {
  const paused = event.currentTarget.textContent === "Pausar";
  event.currentTarget.textContent = paused ? "Reanudar" : "Pausar";
  document.querySelector("#status-copy").textContent = paused ? "Acompañamiento en pausa" : "Acompañamiento activo";
  notify(paused ? "Pausado. No te escribiremos hasta que decidas reanudar." : "Acompañamiento reanudado.");
});

document.querySelector("#open-slack").addEventListener("click", () =>
  notify("Abriendo el DM de Between Sessions en Slack…")
);

document.querySelectorAll("[data-action]").forEach((button) => {
  button.addEventListener("click", () => notify(`Solicitud registrada: ${button.dataset.action}.`));
});
