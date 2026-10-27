document.addEventListener('DOMContentLoaded', async () => {
  const tokenBox = document.getElementById('tokenBox');
  const copyCmdBtn = document.getElementById('copyCmdBtn');
  const copyTokenBtn = document.getElementById('copyTokenBtn');
  const status = document.getElementById('status');

  let currentToken = '';

  try {
    const cookie = await chrome.cookies.get({
      url: 'https://creatorsarea.fr',
      name: 'creators_area_token'
    });

    if (cookie && cookie.value) {
      currentToken = cookie.value;
      tokenBox.textContent = currentToken;
      copyCmdBtn.disabled = false;
      copyTokenBtn.disabled = false;
    } else {
      tokenBox.textContent = 'Aucun cookie trouve. Connectez-vous sur creatorsarea.fr.';
      tokenBox.classList.add('error');
      copyCmdBtn.disabled = true;
      copyTokenBtn.disabled = true;
    }
  } catch (err) {
    tokenBox.textContent = 'Erreur: ' + err.message;
    tokenBox.classList.add('error');
    copyCmdBtn.disabled = true;
    copyTokenBtn.disabled = true;
  }

  copyCmdBtn.addEventListener('click', async () => {
    if (!currentToken) return;
    const cmd = `python run.py --set-token ${currentToken}`;
    await navigator.clipboard.writeText(cmd);
    status.textContent = 'Commande copiee dans le presse-papier';
    setTimeout(() => { status.textContent = ''; }, 3000);
  });

  copyTokenBtn.addEventListener('click', async () => {
    if (!currentToken) return;
    await navigator.clipboard.writeText(currentToken);
    status.textContent = 'Token copie dans le presse-papier';
    setTimeout(() => { status.textContent = ''; }, 3000);
  });
});
