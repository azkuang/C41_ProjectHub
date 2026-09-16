"use strict";
let deferredInstall;
const installButton = document.querySelector('#install');
const installStatus = document.querySelector('#install-status');
window.addEventListener('beforeinstallprompt', event => {
 event.preventDefault(); deferredInstall = event;
 if (installButton) installButton.hidden = false;
});
installButton?.addEventListener('click', async () => {
 if (!deferredInstall) return;
 const prompt = deferredInstall; deferredInstall = undefined; installButton.hidden = true;
 try {
  await prompt.prompt(); const choice = await prompt.userChoice;
  installStatus.textContent = choice.outcome === 'accepted' ? 'Installation requested. Follow your browser’s instructions.' : 'You can also add Project Hub from your browser menu.';
 } catch { installStatus.textContent = 'Please use your browser menu to add Project Hub to your Home Screen.'; }
 installStatus.hidden = false;
});
window.addEventListener('appinstalled', () => {
 deferredInstall = undefined;
 if (installButton) installButton.hidden = true;
 if (installStatus) { installStatus.textContent = 'Project Hub has been installed.'; installStatus.hidden = false; }
});
// Cache only the application shell, never production PDFs or external resources.
if ('serviceWorker' in navigator && (location.protocol === 'https:' || location.hostname === 'localhost' || location.hostname === '127.0.0.1')) {
 navigator.serviceWorker.register('./sw.js').catch(() => {});
}
