---
layout: default
title: How to cite
permalink: /how-to-cite/
---

# How to cite SWUIFT

<p>
  <strong>Authors:</strong>
  {% for author in site.data.citation.authors -%}
    <a href="{{ author.orcid }}">{{ author.name }}</a>
    {%- unless forloop.last -%}
      {%- if forloop.rindex == 2 %}, and {% else %}, {% endif -%}
    {%- endunless -%}
  {%- endfor %}
</p>

<p><strong>Title:</strong> {{ site.data.citation.title }}</p>
<p><strong>Project website:</strong> <a href="{{ site.data.citation.url }}">{{ site.data.citation.url }}</a></p>

{% if site.data.citation.doi %}
<p><strong>DOI:</strong> <a href="https://doi.org/{{ site.data.citation.doi }}">{{ site.data.citation.doi }}</a></p>
{% endif %}

## BibTeX

<pre><code id="citation-bibtex">{{ site.data.citation.bibtex | escape }}</code></pre>
<button id="copy-bibtex" type="button">Copy BibTeX</button>

<script>
  document.getElementById("copy-bibtex").addEventListener("click", async (event) => {
    await navigator.clipboard.writeText({{ site.data.citation.bibtex | jsonify }});
    event.currentTarget.textContent = "Copied";
  });
</script>
