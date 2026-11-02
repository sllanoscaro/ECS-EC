/** Plain Spanish explanations for financial limitations; internal codes remain in captured evidence, not primary task flows. */
const reasons: Record<string, string> = {
  billing_month_unresolved: "Falta resolver el mes de demanda con una política o un documento compatible.",
  physical_general_required: "Se requiere la medición física del suministro general.",
  calculated_general: "El total calculado de categorías no sustituye al medidor general.",
  no_source: "No hay una fuente física general disponible.",
  insufficient_evidence: "La cobertura de mediciones es insuficiente.",
  insufficient_energy_coverage: "No hay energía física completa para este tramo de vigencia.",
  insufficient_demand_history: "Faltan bloques completos para demostrar los máximos históricos.",
  insufficient_demand_resolution: "La resolución disponible no permite determinar la demanda de quince minutos.",
  monetary_precision_exceeded: "El importe excede el rango o la precisión documentada; revise el precio y la política de redondeo.",
  missing_price: "Falta un precio aplicable documentado.",
  missing_documented_source: "Falta documentar la fuente de esta condición o cargo.",
  required_charge_missing: "Falta un cargo declarado aplicable en el perfil.",
  profile_unavailable: "No hay una revisión publicada del perfil.",
  profile_validity_gap: "El calendario del perfil no cubre todo el ciclo.",
  charge_validity_gap: "El cargo no tiene una vigencia resuelta en todo el ciclo.",
  monthly_strategy_unresolved: "No está resuelta la regla mensual del cargo; no se prorratea automáticamente.",
  unsupported_charge_rule: "La regla documentada del cargo aún no está soportada.",
  unsupported_applicability: "No está resuelta la condición de aplicación del cargo.",
  unsupported_historical_rule: "La regla histórica aún no está soportada.",
  unsupported_peak_alignment: "El horario documentado de punta no coincide con bloques completos de quince minutos.",
  tax_rule_unresolved: "Falta resolver la regla tributaria del cargo.",
  tax_basis_unresolved: "No hay una base tributaria compatible; no se vuelve a aplicar un impuesto incluido.",
  cycle_boundaries_unresolved: "Falta confirmar los límites efectivos del ciclo.",
  supply_conditions_missing: "Faltan condiciones o fuentes documentales del suministro.",
  engine_failed: "No se pudo completar el cálculo; quedó registrada una revisión fallida.",
  no_comparable_pairs: "No hay conceptos con bases compatibles para comparar.",
  outside_comparable_cycle: "Concepto ajeno al ciclo comparable.",
  no_calculated_equivalent: "El concepto no tiene un equivalente calculado.",
  calculation_limited: "El concepto calculado no tiene un importe disponible.",
  quantity_basis_mismatch: "Las unidades o bases de cantidad no coinciden.",
  tax_basis_mismatch: "Las bases tributarias no pueden alinearse con los datos declarados.",
};

/** Explain only known functional causes; unknown codes get a safe useful limitation rather than raw implementation text. */
export function limitationLabel(code: string) { return reasons[code] ?? "Hay una condición pendiente de resolver con la evidencia disponible."; }

/** Translate the closed financial rule catalog while retaining detailed version evidence elsewhere. */
export function ruleLabel(code: string) {
  return ({ exact_intervals: "Energía por intervalos exactos", cycle_once: "Cargo del ciclo según política documentada", captured_total_rounding: "Ajuste de redondeo al total" } as Record<string,string>)[code] ?? "Regla documentada no resuelta";
}
