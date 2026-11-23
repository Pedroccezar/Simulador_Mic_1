const ALU_OP = ["A + B", "A AND B", "A", "NOT A"];
const COND_TXT = ["Não desvia", "Se N=1", "Se Z=1", "Sempre"];

let exemplos = [];

async function getJSON(url) {
  return (await fetch(url)).json();
}

async function postJSON(url, body = {}) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return res.json();
}

function mostrarAviso(texto, tipo = "ok") {
  const el = document.getElementById("msg-montador");
  el.textContent = texto;
  el.className = `aviso ${tipo}`;
}

function render(est) {
  // Topo
  document.getElementById("cnt-micro").textContent = est.ciclos_micro;
  document.getElementById("cnt-macro").textContent = est.macro_executadas;
  const st = document.getElementById("badge-status");
  if (est.finalizado) {
    st.textContent = "Finalizado";
    st.classList.add("halt");
  } else {
    st.textContent = est.ciclos_micro > 0 ? `MPC ${est.mpc}` : "Pronto";
    st.classList.remove("halt");
  }

  renderSVG(est);
  renderRastro(est.rastro);
  renderListagem(est);
  renderRegistradores(est);
  renderCache(est.cache_instrucoes, "tbody-icache", "icache-badge", "icache-info");
  renderCache(est.cache_dados, "tbody-dcache", "dcache-badge", "dcache-info");
  renderMemoria(est);

  document.querySelectorAll("#tbody-rom tr").forEach((tr) => {
    tr.classList.toggle("dest-mpc", Number(tr.dataset.mpc) === est.mpc);
  });
}

function renderSVG(est) {
  document.querySelectorAll("#svg-mic1 .ativo, #svg-mic1 .cache-hit, #svg-mic1 .cache-miss").forEach((el) => {
    el.classList.remove("ativo", "cache-hit", "cache-miss");
  });

  const r = est.registradores;
  document.getElementById("svg-pc").textContent = r[0].valor_u16;
  document.getElementById("svg-ac").textContent = r[1].valor_s16;
  document.getElementById("svg-sp").textContent = r[2].valor_u16;
  document.getElementById("svg-ir").textContent = r[3].hex;
  document.getElementById("svg-tir").textContent = r[4].hex;
  document.getElementById("svg-regA").textContent = r[10].valor_s16;

  document.getElementById("svg-mar").textContent = `${est.mar_hex} (${est.mar})`;
  document.getElementById("svg-mbr").textContent = `${est.mbr_hex} (${est.mbr_s16})`;
  document.getElementById("svg-latch-a").textContent = est.latch_a_s16;
  document.getElementById("svg-latch-b").textContent = est.latch_b_s16;

  const mir = est.mir;
  document.getElementById("svg-amux").textContent = mir.amux ? "MBR" : "Latch A";
  document.getElementById("svg-ula-op").textContent = `${ALU_OP[mir.alu]} = ${est.saida_ula_s16}`;
  document.getElementById("svg-ula-flags").textContent = `N=${est.flag_n}  Z=${est.flag_z}`;
  document.getElementById("svg-sh").textContent = `Saída: ${est.saida_deslocador_s16}`;

  document.getElementById("svg-mpc").textContent = est.mpc;
  document.getElementById("svg-inc").textContent = `${(est.mpc + 1) & 0xff}`;
  document.getElementById("svg-mmux").textContent = est.mmux_desviou ? `ADDR (${mir.addr})` : "MPC + 1";
  document.getElementById("svg-micro-txt").textContent = mir.texto;
  document.getElementById("svg-micro-prox").textContent = `Próx. MPC ${est.mpc}: ${est.mir_proximo.texto}`;

  const sinais = [];
  if (mir.amux) sinais.push("AMUX=MBR");
  if (mir.mar) sinais.push("MAR");
  if (mir.mbr) sinais.push("MBR");
  if (mir.rd) sinais.push("RD");
  if (mir.wr) sinais.push("WR");
  if (mir.enc) sinais.push(`C=${mir.c_nome}`);
  sinais.push(`A=${mir.a_nome}`, `B=${mir.b_nome}`);
  document.getElementById("svg-mir-sinais").textContent = sinais.join(" • ");
  document.getElementById("svg-mir-hex").textContent = mir.hex32;

  document.getElementById("svg-seq").textContent =
    `${COND_TXT[mir.cond]} (N=${est.flag_n}, Z=${est.flag_z}) → ${est.mmux_desviou ? "ADDR " + mir.addr : "MPC + 1"}`;

  const ic = est.cache_instrucoes;
  const dc = est.cache_dados;
  document.getElementById("svg-icache").textContent = `Hits: ${ic.hits} | Misses: ${ic.misses} (${ic.taxa_hit}%)`;
  document.getElementById("svg-dcache").textContent = `Hits: ${dc.hits} | Misses: ${dc.misses} (${dc.taxa_hit}%)`;

  (est.rastro.ativos || []).forEach((id) => {
    const el = document.getElementById(`comp-${id}`);
    if (el) el.classList.add("ativo");
  });

  if (est.rastro.evento_cache && est.rastro.cache_usada) {
    const el = document.getElementById(`comp-${est.rastro.cache_usada}`);
    if (el) {
      el.classList.remove("ativo");
      el.classList.add(est.rastro.evento_cache.resultado === "HIT" ? "cache-hit" : "cache-miss");
    }
  }
}

function renderRastro(rastro) {
  const titulo = rastro.mpc_executado !== null ? `MPC ${rastro.mpc_executado}: ${rastro.micro_texto}` : rastro.micro_texto;
  document.getElementById("rastro-titulo").textContent = titulo;
  document.getElementById("rastro-desc").textContent = rastro.descricao || "";
  const ol = document.getElementById("lista-subciclos");
  ol.innerHTML = "";
  (rastro.subciclos || []).forEach((txt) => {
    const li = document.createElement("li");
    li.textContent = txt;
    ol.appendChild(li);
  });
}

function renderListagem(est) {
  const pc = est.registradores[0].valor_u16;
  const tbody = document.getElementById("tbody-listagem");
  tbody.innerHTML = "";
  (est.listagem || []).forEach((it) => {
    const tr = document.createElement("tr");
    if (it.endereco === pc && !it.eh_dado) tr.className = "dest-pc";
    tr.innerHTML = `
      <td>${it.endereco}</td>
      <td>${it.hex}</td>
      <td>${it.binario}</td>
      <td>${it.rotulo ? `<b>${it.rotulo}:</b> ` : ""}${it.fonte}</td>
    `;
    tbody.appendChild(tr);
  });
}

function renderRegistradores(est) {
  document.getElementById("mir-hex").textContent = est.mir.hex32;
  document.getElementById("mir-bin").textContent = est.mir.bits32;

  const tbody = document.getElementById("tbody-regs");
  tbody.innerHTML = "";
  est.registradores.forEach((r) => {
    const tr = document.createElement("tr");
    if (r.constante) tr.className = "reg-const";
    tr.innerHTML = `<td><b>${r.nome}</b></td><td>${r.valor_s16}</td><td>${r.hex}</td><td>${r.binario}</td>`;
    tbody.appendChild(tr);
  });
}

function renderCache(c, tbodyId, badgeId, infoId) {
  document.getElementById(badgeId).textContent = `${c.taxa_hit}% hit (${c.hits}/${c.acessos})`;
  document.getElementById(infoId).textContent =
    `${c.modo} • ${c.num_conjuntos} conj. × ${c.palavras_por_bloco} palavras (Tag ${c.bits_tag}b | Índ ${c.bits_indice}b | Off ${c.bits_offset}b)`;

  const tbody = document.getElementById(tbodyId);
  tbody.innerHTML = "";
  const ult = c.ultimo_evento;
  c.linhas.forEach((l) => {
    const tr = document.createElement("tr");
    if (ult && ult.conjunto === l.conjunto && ult.via === l.via) {
      tr.className = ult.resultado === "HIT" ? "dest-hit" : "dest-miss";
    }
    const dados = l.valido ? l.dados.map((v) => v.toString(16).toUpperCase().padStart(4, "0")).join(" ") : "—";
    tr.innerHTML = `
      <td>${l.conjunto}</td>
      <td>${l.via}</td>
      <td>${l.valido ? 1 : 0}</td>
      <td>${l.valido ? "0x" + l.tag.toString(16).toUpperCase() : "—"}</td>
      <td>${dados}</td>
    `;
    tbody.appendChild(tr);
  });
}

function renderMemoria(est) {
  const pc = est.registradores[0].valor_u16;
  const sp = est.registradores[2].valor_u16;
  const mar = est.mar;
  const tbody = document.getElementById("tbody-mem");
  tbody.innerHTML = "";
  est.memoria.forEach((m) => {
    const tr = document.createElement("tr");
    let tags = "";
    if (m.endereco === pc) { tr.classList.add("dest-pc"); tags += `<span class="tag tag-pc">PC</span>`; }
    if (m.endereco === mar) { if (!tr.className) tr.classList.add("dest-mar"); tags += `<span class="tag tag-mar">MAR</span>`; }
    if (m.endereco === sp) { if (!tr.className) tr.classList.add("dest-sp"); tags += `<span class="tag tag-sp">SP</span>`; }
    tr.innerHTML = `
      <td>${m.endereco}${tags}</td>
      <td>${m.rotulo}</td>
      <td>${m.valor_s16}</td>
      <td>${m.hex}</td>
      <td>${m.desmontado}</td>
    `;
    tbody.appendChild(tr);
  });
}

/* EVENTOS */
document.getElementById("btn-micro").addEventListener("click", async () => {
  const r = await postJSON("/api/passo_micro");
  if (r.ok) render(r.estado);
});

document.getElementById("btn-macro").addEventListener("click", async () => {
  const r = await postJSON("/api/passo_macro");
  if (r.ok) render(r.estado);
});

document.getElementById("btn-executar").addEventListener("click", async () => {
  const r = await postJSON("/api/executar", { limite: 500 });
  if (r.ok) render(r.estado);
});

document.getElementById("btn-reset").addEventListener("click", async () => {
  const r = await postJSON("/api/reset");
  if (r.ok) render(r.estado);
});

document.getElementById("btn-montar").addEventListener("click", async () => {
  const codigo = document.getElementById("editor-asm").value;
  const r = await postJSON("/api/montar", { codigo });
  if (r.ok) {
    mostrarAviso("Programa montado e carregado na memória.", "ok");
    render(r.estado);
  } else {
    mostrarAviso(r.erro || "Erro ao montar.", "erro");
  }
});

document.getElementById("select-exemplo").addEventListener("change", async (e) => {
  const ex = exemplos[Number(e.target.value)];
  if (!ex) return;
  document.getElementById("editor-asm").value = ex.codigo;
  const r = await postJSON("/api/montar", { codigo: ex.codigo });
  if (r.ok) {
    mostrarAviso(`Exemplo "${ex.titulo}" carregado.`, "ok");
    render(r.estado);
  }
});

document.getElementById("btn-cache").addEventListener("click", async () => {
  const vias = Number(document.getElementById("cfg-vias").value);
  const num_conjuntos = Number(document.getElementById("cfg-conjuntos").value);
  const r = await postJSON("/api/config_cache", { vias, num_conjuntos, palavras_por_bloco: 4 });
  if (r.ok) render(r.estado);
});

document.querySelectorAll(".aba").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".aba").forEach((b) => b.classList.remove("ativa"));
    document.querySelectorAll(".painel-aba").forEach((p) => p.classList.remove("ativo"));
    btn.classList.add("ativa");
    document.getElementById(btn.dataset.aba).classList.add("ativo");
  });
});

(async function init() {
  const romData = await getJSON("/api/microprograma");
  const tbodyRom = document.getElementById("tbody-rom");
  romData.microprograma.forEach((mi) => {
    const tr = document.createElement("tr");
    tr.dataset.mpc = mi.endereco;
    tr.innerHTML = `<td><b>${mi.endereco}</b></td><td>${mi.texto}</td><td>${mi.hex32}</td>`;
    tbodyRom.appendChild(tr);
  });

  const exData = await getJSON("/api/exemplos");
  exemplos = exData.exemplos || [];
  const sel = document.getElementById("select-exemplo");
  exemplos.forEach((ex, i) => {
    const opt = document.createElement("option");
    opt.value = i;
    opt.textContent = ex.titulo;
    sel.appendChild(opt);
  });
  if (exemplos.length) document.getElementById("editor-asm").value = exemplos[0].codigo;

  render(await getJSON("/api/estado"));
})();
