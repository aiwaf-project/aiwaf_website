/* Progressive documentation tools. Reading and navigation work without JS. */
(() => {
  const content = document.querySelector('main.content');
  if (!content) return;

  const headings = [...content.querySelectorAll('h2')];
  if (headings.length > 1) {
    const toc = document.createElement('nav');
    toc.className = 'docs-toc';
    toc.setAttribute('aria-label', 'On this page');
    const label = document.createElement('strong');
    label.textContent = 'On this page';
    const list = document.createElement('ul');
    headings.forEach((heading, index) => {
      if (!heading.id) {
        const base = heading.textContent.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || `section-${index}`;
        let id = base;
        let suffix = 2;
        while (document.getElementById(id)) id = `${base}-${suffix++}`;
        heading.id = id;
      }
      const item = document.createElement('li');
      const link = document.createElement('a');
      link.href = `#${heading.id}`;
      link.textContent = heading.textContent;
      item.append(link);
      list.append(item);
    });
    toc.append(label, list);
    const lead = content.querySelector('.docs-lead') || content.querySelector('h1');
    if (lead) lead.insertAdjacentElement('afterend', toc);
  }

  content.querySelectorAll('pre > code').forEach((code) => {
    const pre = code.parentElement;
    const toolbar = document.createElement('div');
    toolbar.className = 'docs-code-toolbar';
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = 'Copy code';
    button.setAttribute('aria-label', 'Copy this code block');
    const status = document.createElement('span');
    status.setAttribute('role', 'status');
    button.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(code.textContent);
        status.textContent = 'Copied';
      } catch {
        const selection = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(code);
        selection.removeAllRanges();
        selection.addRange(range);
        status.textContent = 'Code selected. Use your copy shortcut.';
      }
    });
    toolbar.append(button, status);
    pre.insertAdjacentElement('beforebegin', toolbar);
  });

  const search = document.querySelector('[data-docs-search]');
  if (!search) return;
  const input = search.querySelector('input');
  const results = search.querySelector('ol');
  const status = search.querySelector('[role="status"]');
  const panel = search.querySelector('.docs-search-panel');
  let indexPromise;
  let generation = 0;
  const updateSearch = async () => {
    const current = ++generation;
    const query = input.value.trim().toLowerCase();
    results.replaceChildren();
    panel.hidden = query.length < 2;
    if (query.length < 2) {
      status.textContent = 'Enter at least two characters.';
      return;
    }
    status.textContent = 'Searching documentation...';
    try {
      indexPromise ||= fetch('/static/docs-search-index.json').then((response) => {
        if (!response.ok) throw new Error('Index unavailable');
        return response.json();
      }).catch((error) => { indexPromise = null; throw error; });
      const pages = await indexPromise;
      if (current !== generation) return;
      const words = query.split(/\s+/);
      const matches = pages.filter((page) => words.every((word) => `${page.title} ${page.text}`.toLowerCase().includes(word)))
        .map((page) => ({...page, score: words.reduce((total, word) => total + (page.title.toLowerCase().includes(word) ? 10 : 1), 0)}))
        .sort((a, b) => b.score - a.score).slice(0, 8);
      matches.forEach((page) => {
        const item = document.createElement('li');
        const link = document.createElement('a');
        link.href = page.url;
        link.textContent = page.title;
        const excerpt = document.createElement('p');
        const start = Math.max(0, page.text.toLowerCase().indexOf(words[0]) - 50);
        excerpt.textContent = page.text.slice(start, start + 180) + (page.text.length > start + 180 ? '...' : '');
        item.append(link, excerpt);
        results.append(item);
      });
      status.textContent = matches.length ? `Showing ${matches.length} matching pages.` : 'No matching pages. Try a setting name, framework, or task.';
    } catch {
      if (current === generation) status.textContent = 'Search could not load. Use the documentation navigation links.';
    }
  };
  input.addEventListener('input', updateSearch);
  input.addEventListener('focus', updateSearch);
  search.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      input.focus();
      panel.hidden = true;
    }
  });
  document.addEventListener('pointerdown', (event) => {
    if (!search.contains(event.target)) panel.hidden = true;
  });
  search.addEventListener('focusout', (event) => {
    if (!search.contains(event.relatedTarget)) panel.hidden = true;
  });
})();
