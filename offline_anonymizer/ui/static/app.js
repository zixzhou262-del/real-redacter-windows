const TOKEN_SELECTOR = "[data-token-id]";

document.addEventListener("click", (event) => {
  const token = event.target.closest(TOKEN_SELECTOR);
  if (!token) {
    return;
  }
  token.classList.toggle("is-selected");
});
