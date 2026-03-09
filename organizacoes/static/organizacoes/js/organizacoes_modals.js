function renderOptions(evt, selectId, labelKey, sliceLength) {
    const sel = document.querySelector(selectId);
    if (!sel) return;
    sel.innerHTML = '';
    try {
        const data = JSON.parse(evt.detail.xhr.response);
        const itens = data.results || data;
        sel.innerHTML =
            itens
                .map(item => {
                    let label = item[labelKey] ?? '';
                    if (sliceLength) {
                        label = label.slice(0, sliceLength);
                    }
                    return `<option value="${item.id}">${label}</option>`;
                })
                .join('') || `<option value="">${gettext('Nenhum resultado')}</option>`;
    } catch (err) {
        sel.innerHTML = `<option value="">${gettext('Erro ao carregar')}</option>`;
    }
}
