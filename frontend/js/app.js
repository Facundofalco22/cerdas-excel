const $ = (id) => document.getElementById(id);
const esc = (t) => String(t ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

// =====================================================================
//  EXCEL DE TRABAJO
// =====================================================================
async function actualizarEstadoExcel() {
  try {
    const e = await (await fetch("/api/excel/estado")).json();
    $("estado-excel").textContent = e.existe
      ? `Usando: ${e.origen} · ${e.hojas} cerdas · última modificación ${e.modificado}`
      : "No hay ningún Excel cargado. Cargá el Excel completo para empezar.";
  } catch (err) {
    $("estado-excel").textContent = "No se pudo consultar el Excel.";
  }
}

$("archivo-excel").addEventListener("change", async (ev) => {
  const archivo = ev.target.files[0];
  if (!archivo) return;
  const datos = new FormData();
  datos.append("archivo", archivo);
  $("msg-excel").className = "chico";
  $("msg-excel").textContent = "Cargando el Excel...";
  const r = await fetch("/api/excel/cargar", { method: "POST", body: datos });
  const res = await r.json();
  if (r.ok) {
    $("msg-excel").className = "chico ok";
    $("msg-excel").textContent = `✅ Excel cargado: ${res.hojas} cerdas. Ya podés buscar y agregar datos.`;
  } else {
    $("msg-excel").className = "chico error";
    $("msg-excel").textContent = "❌ " + res.detail;
  }
  ev.target.value = "";
  actualizarEstadoExcel();
});

$("btn-reiniciar").addEventListener("click", async () => {
  if (!confirm("Se descarta lo cargado y guardado desde la web y se vuelve a la planilla original. ¿Seguro?")) return;
  await fetch("/api/excel/reiniciar", { method: "POST" });
  $("msg-excel").className = "chico";
  $("msg-excel").textContent = "Se volvió a la planilla original.";
  actualizarEstadoExcel();
});

// =====================================================================
//  BUSCAR CERDA
// =====================================================================
async function buscarCerda() {
  const nro = $("buscar-nro").value.trim();
  const caja = $("resultado-busqueda");
  if (!nro) return;
  const r = await fetch("/api/cerda/" + encodeURIComponent(nro));
  const res = await r.json();
  if (!r.ok) {
    caja.innerHTML = `<p class="error">${esc(res.detail || "Error al buscar")}</p>`;
    return;
  }
  if (!res.hoja && !res.en_indice) {
    caja.innerHTML = `<p class="aviso">La cerda ${esc(nro)} no está en el Excel.</p>`;
    return;
  }
  let html = `<h3>Cerda ${esc(res.cerda)}`;
  if (res.indice) {
    html += ` · Registros: ${esc(res.indice.registros ?? "-")} · Último servicio: ${esc(res.indice.ultimo_servicio ?? "-")}`;
  }
  html += `</h3>`;
  if (!res.hoja) {
    html += `<p class="aviso">Figura en el índice pero todavía no tiene hoja con registros.</p>`;
  } else if (!res.registros.length) {
    html += `<p class="aviso">La hoja existe pero no tiene registros cargados.</p>`;
  } else {
    html += `<div class="scroll"><table><thead><tr>${res.columnas.map((c) => `<th>${esc(c)}</th>`).join("")}</tr></thead><tbody>`;
    res.registros.forEach((f) => {
      html += `<tr>${f.map((v) => `<td>${esc(v)}</td>`).join("")}</tr>`;
    });
    html += `</tbody></table></div>`;
  }
  caja.innerHTML = html;
}
$("btn-buscar").addEventListener("click", buscarCerda);
$("buscar-nro").addEventListener("keydown", (e) => { if (e.key === "Enter") buscarCerda(); });

// =====================================================================
//  FOTOS
// =====================================================================
const inputFotos = $("fotos");
let archivos = [];

function mostrarArchivos() {
  $("lista-fotos").textContent = archivos.length
    ? archivos.length + " foto(s): " + archivos.map((a) => a.name).join(", ")
    : "";
  $("btn-leer").disabled = archivos.length === 0;
}
inputFotos.addEventListener("change", () => { archivos = [...inputFotos.files]; mostrarArchivos(); });
const zona = $("zona");
zona.addEventListener("dragover", (e) => { e.preventDefault(); zona.classList.add("sobre"); });
zona.addEventListener("dragleave", () => zona.classList.remove("sobre"));
zona.addEventListener("drop", (e) => {
  e.preventDefault(); zona.classList.remove("sobre");
  archivos = [...e.dataTransfer.files].filter((f) => f.type.startsWith("image/"));
  mostrarArchivos();
});

$("btn-leer").addEventListener("click", async () => {
  const datos = new FormData();
  archivos.forEach((f) => datos.append("fotos", f));
  datos.append("giro", $("giro").value);
  $("btn-leer").disabled = true;
  $("estado").textContent = "Enderezando y leyendo las fotos... puede tardar unos segundos.";
  try {
    const r = await fetch("/api/upload", { method: "POST", body: datos });
    const res = await r.json();
    res.filas.forEach(agregarFila);
    const giros = Object.entries(res.giros || {})
      .map(([n, g]) => `${n}: girada ${g}°`).join(" | ");
    $("estado").textContent = res.filas.length + " fila(s) leída(s)." +
      (giros ? " (" + giros + ")" : "") +
      (res.errores.length ? " Problemas: " + res.errores.join(" | ") : "");
    if (res.filas.length) $("revision").hidden = false;
  } catch (e) {
    $("estado").textContent = "Error de conexión: " + e;
  }
  $("btn-leer").disabled = false;
});

// =====================================================================
//  FECHAS CON BARRAS AUTOMÁTICAS (dd/mm/aaaa)
// =====================================================================
function mascaraFecha(digitos) {
  const d = digitos.slice(0, 8);
  let out = d.slice(0, 2);
  if (d.length >= 2) out += "/";
  if (d.length > 2) out += d.slice(2, 4);
  if (d.length >= 4) out += "/";
  if (d.length > 4) out += d.slice(4, 8);
  return out;
}

// Convierte "5-3-26", "27.3.2026", "27/03/2026" en "05/03/2026" / "27/03/2026"
function normalizarFechaCompleta(texto) {
  const m = texto.trim().match(/^(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{2}|\d{4})$/);
  if (!m) return null;
  const anio = m[3].length === 2 ? "20" + m[3] : m[3];
  return m[1].padStart(2, "0") + "/" + m[2].padStart(2, "0") + "/" + anio;
}

function fechaValida(texto) {
  if (!texto) return true;                       // vacío = no hay fecha, está bien
  const m = texto.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
  if (!m) return false;
  const [d, mes, a] = [+m[1], +m[2], +m[3]];
  const f = new Date(a, mes - 1, d);
  return f.getFullYear() === a && f.getMonth() === mes - 1 && f.getDate() === d;
}

function activarMascaraFecha(inp) {
  inp.inputMode = "numeric";
  inp.maxLength = 10;
  inp.addEventListener("input", (e) => {
    const borrando = (e.inputType || "").startsWith("delete");
    let digitos = inp.value.replace(/\D/g, "");
    // si escribieron "/" "-" o "." después de un solo dígito (día o mes), se completa con 0
    if (!borrando && /^[\/\-.]$/.test(e.data || "")) {
      if (digitos.length === 1) digitos = "0" + digitos;
      else if (digitos.length === 3) digitos = digitos.slice(0, 2) + "0" + digitos[2];
    }
    let out = mascaraFecha(digitos);
    if (borrando && out.endsWith("/")) out = out.slice(0, -1);
    inp.value = out;
    inp.classList.toggle("invalida", out.length === 10 && !fechaValida(out));
  });
  inp.addEventListener("paste", (e) => {
    const texto = (e.clipboardData || window.clipboardData).getData("text");
    const completa = normalizarFechaCompleta(texto);
    e.preventDefault();
    inp.value = completa || mascaraFecha(texto.replace(/\D/g, ""));
    inp.dispatchEvent(new Event("blur"));
  });
  inp.addEventListener("blur", () => {
    const completa = normalizarFechaCompleta(inp.value);   // 5/3/26 -> 05/03/2026
    if (completa) inp.value = completa;
    inp.classList.toggle("invalida", !fechaValida(inp.value));
  });
  inp.classList.toggle("invalida", !fechaValida(inp.value));
}

// =====================================================================
//  TABLA EDITABLE
// =====================================================================
const CAMPOS = [
  ["cerda", "number"], ["fecha_servicio", "fecha"], ["padrillo", "text"],
  ["fecha_parto_probable", "fecha"], ["fecha_parto", "fecha"],
  ["nacidos_vivos", "number"], ["nacidos_totales", "number"],
  ["fecha_destete", "fecha"], ["destetados", "number"],
];

function agregarFila(f = {}) {
  const tr = document.createElement("tr");
  CAMPOS.forEach(([campo, tipo]) => {
    const td = document.createElement("td");
    const inp = document.createElement("input");
    inp.type = tipo === "number" ? "number" : "text";
    inp.dataset.campo = campo;
    inp.value = f[campo] ?? "";
    if (tipo === "fecha") { inp.className = "fecha"; inp.placeholder = "dd/mm/aaaa"; activarMascaraFecha(inp); }
    td.appendChild(inp); tr.appendChild(td);
  });
  const tdV = document.createElement("td");
  const chk = document.createElement("input");
  chk.type = "checkbox"; chk.dataset.campo = "no_gesto"; chk.checked = !!f.no_gesto;
  chk.addEventListener("change", () => tr.classList.toggle("verde", chk.checked));
  tdV.appendChild(chk); tr.appendChild(tdV);
  const tdN = document.createElement("td");
  const nota = document.createElement("input");
  nota.type = "text"; nota.className = "nota"; nota.dataset.campo = "nota"; nota.value = f.nota || "";
  tdN.appendChild(nota); tr.appendChild(tdN);
  const tdX = document.createElement("td");
  const x = document.createElement("button"); x.textContent = "✕";
  x.addEventListener("click", () => tr.remove());
  tdX.appendChild(x); tr.appendChild(tdX);
  tr.classList.toggle("dudoso", !!f.dudoso);
  tr.classList.toggle("verde", !!f.no_gesto);
  $("filas").appendChild(tr);
}
$("btn-agregar").addEventListener("click", () => agregarFila());

function leerTabla() {
  return [...$("filas").children].map((tr) => {
    const fila = {};
    tr.querySelectorAll("[data-campo]").forEach((el) => {
      fila[el.dataset.campo] = el.type === "checkbox" ? el.checked : el.value.trim();
    });
    return fila;
  });
}

// =====================================================================
//  GUARDAR
// =====================================================================
$("btn-guardar").addEventListener("click", async () => {
  const lista = $("errores"); lista.innerHTML = "";
  const r = await fetch("/api/guardar", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(leerTabla()),
  });
  const res = await r.json();
  if (!r.ok) {
    (res.detail || ["Error al guardar"]).forEach((m) => {
      const li = document.createElement("li"); li.textContent = m; lista.appendChild(li);
    });
    return;
  }
  $("filas").innerHTML = "";
  $("revision").hidden = true;
  $("estado").textContent = "✅ Se guardaron " + res.guardadas + " fila(s) en el Excel. Ya podés descargarlo o buscar la cerda arriba.";
  actualizarEstadoExcel();
});

actualizarEstadoExcel();