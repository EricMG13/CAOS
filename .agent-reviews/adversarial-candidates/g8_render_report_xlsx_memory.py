def render_report_xlsx(*, version_id: str, document_sha256: str, payload: dict, authority: dict) -> bytes:
    document = payload.get("document") if isinstance(payload.get("document"), dict) else {}
    reviewed = _reviewed_report(payload)
    modules = (
        [] if reviewed
        else document.get("sections") if isinstance(document.get("sections"), list) else []
    )
    model = payload.get("model") if isinstance(payload.get("model"), dict) else {}
    calculation = model.get("calculation") if isinstance(model.get("calculation"), dict) else {}
    reporting_currency, reporting_unit, reporting_scale = _model_reporting_metadata(
        model
    )
    override_rows, omitted_override_count = _model_override_rows(
        model,
        report_event_at=authority.get("as_of"),
    )
    freshness = authority.get("freshness_evaluation") if isinstance(authority.get("freshness_evaluation"), dict) else {}
    freshness_state = _display(freshness.get("state") or authority.get("freshness") or "unknown").upper()
    wb = Workbook()
    header_font = Font(name="Arial", bold=True, color="FFFFFF")
    navy_fill = PatternFill("solid", fgColor=_NAVY)
    blue_fill = PatternFill("solid", fgColor=_BLUE)
    header_alignment = Alignment(wrap_text=True)
    body_font = Font(name="Arial", size=9, color=_INK)
    metadata_font = Font(name="Arial", bold=True, color=_MUTED)
    module_title_font = Font(name="Arial", size=15, bold=True, color="FFFFFF")
    module_title_alignment = Alignment(vertical="center", indent=1)
    top_wrap_alignment = Alignment(vertical="top", wrap_text=True)
    thin = Side(style="thin", color="D8DCE5")
    row_border = Border(bottom=thin)

    cover = wb.active
    cover.title = "Cover"
    cover.sheet_view.showGridLines = False
    cover.freeze_panes = "A8"
    cover["A1"] = "CAOS - IMMUTABLE COMMITTEE REPORT"
    cover["A1"].font = Font(name="Arial", size=18, bold=True, color="FFFFFF")
    cover["A1"].fill = navy_fill
    cover.merge_cells("A1:D2")
    cover["A1"].alignment = Alignment(vertical="center")
    metadata = (
        ("Report version", version_id),
        ("Document SHA-256", document_sha256),
        ("Issuer", document.get("issuer_id")),
        ("Run", document.get("run_id")),
        ("As of", document.get("as_of_date")),
        ("QA status", document.get("qa_status")),
        ("Committee status", document.get("committee_status")),
        ("Prepared by", document.get("prepared_by")),
        ("Authority origin", authority.get("origin")),
        ("Authority state", authority.get("approval_state")),
        ("Freshness", freshness_state),
        ("Freshness source", freshness.get("source_kind")),
        ("Freshness reason", freshness.get("reason")),
        ("Freshness policy", freshness.get("policy_version")),
        ("Freshness observed", freshness.get("observed_at")),
        ("Freshness effective period", freshness.get("effective_period_end")),
        ("Freshness due", freshness.get("due_at")),
        ("Model engine", model.get("engine_version")),
        ("Model source fingerprint", model.get("source_fingerprint")),
        ("Model input fingerprint", model.get("input_fingerprint")),
        ("Model calculation hash", model.get("calculation_hash")),
        ("Model draft revision", model.get("draft_revision")),
        ("Model origin", (model.get("authority") or {}).get("origin") if isinstance(model.get("authority"), dict) else None),
        ("Model input origins", ", ".join((model.get("authority") or {}).get("model_input_origins") or []) if isinstance(model.get("authority"), dict) else None),
        ("Model analyst override", (model.get("authority") or {}).get("analyst_override") if isinstance(model.get("authority"), dict) else None),
        ("Model availability", calculation.get("status")),
        ("Model reporting currency", reporting_currency),
        ("Model reporting unit", reporting_unit),
        ("Model override count", len(override_rows) + omitted_override_count),
    )
    for row_index, (label, value) in enumerate(metadata, start=4):
        cover.cell(row_index, 1, label).font = metadata_font
        cover.cell(row_index, 2, _xlsx_text(value))
    cover.column_dimensions["A"].width = 24
    cover.column_dimensions["B"].width = 72
    cover.column_dimensions["C"].width = 18
    cover.column_dimensions["D"].width = 18
    cover.sheet_properties.pageSetUpPr.fitToPage = True
    cover.page_setup.fitToWidth = 1
    cover.page_setup.fitToHeight = 0

    if reviewed:
        reviewed_sheet = wb.create_sheet("Reviewed Report")
        reviewed_sheet.sheet_view.showGridLines = False
        reviewed_sheet.freeze_panes = "A2"
        reviewed_sheet.append(["Section", "Field", "Reviewed value"])
        for cell in reviewed_sheet[1]:
            cell.font = header_font
            cell.fill = navy_fill
            cell.alignment = header_alignment
        for section, field, value in _reviewed_rows(reviewed):
            reviewed_sheet.append([
                _xlsx_text(section), _xlsx_text(field), _xlsx_scalar(value),
            ])
        reviewed_sheet.column_dimensions["A"].width = 42
        reviewed_sheet.column_dimensions["B"].width = 38
        reviewed_sheet.column_dimensions["C"].width = 110
        for row in reviewed_sheet.iter_rows(min_row=2):
            for cell in row:
                cell.alignment = top_wrap_alignment
                cell.font = body_font

    summary = wb.create_sheet("Module Summary")
    summary.sheet_view.showGridLines = False
    summary.freeze_panes = "A2"
    summary.append(["Module", "Name", "Confidence", "QA status"])
    for module in modules:
        if not isinstance(module, dict):
            continue
        summary.append([
            _xlsx_text(module.get("module_id")),
            _xlsx_text(module.get("module_name")),
            _xlsx_scalar(module.get("confidence")),
            _xlsx_text(module.get("qa_status")),
        ])
    for cell in summary[1]:
        cell.font = header_font
        cell.fill = navy_fill
    summary.column_dimensions["A"].width = 16
    summary.column_dimensions["B"].width = 42
    summary.column_dimensions["C"].width = 16
    summary.column_dimensions["D"].width = 18
    if summary.max_row > 1:
        table = Table(displayName="ModuleSummary", ref=f"A1:D{summary.max_row}")
        table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True, showFirstColumn=False, showLastColumn=False)
        summary.add_table(table)

    used = {sheet.title for sheet in wb.worksheets}
    for module_index, module in enumerate(modules, start=1):
        if not isinstance(module, dict):
            continue
        module_id = _display(module.get("module_id")) or f"Module {module_index}"
        sheet = wb.create_sheet(_safe_sheet_name(module_id, used))
        sheet.sheet_view.showGridLines = False
        sheet.freeze_panes = "A5"
        sheet["A1"] = _xlsx_text(f"{module_id} - {_display(module.get('module_name'))}")
        sheet["A1"].font = module_title_font
        sheet["A1"].fill = navy_fill
        sheet["A1"].alignment = module_title_alignment
        sheet.merge_cells("A1:B2")
        sheet["A3"] = "Path"
        sheet["B3"] = "Frozen value"
        for cell in sheet[3]:
            cell.font = header_font
            cell.fill = blue_fill
        rendered_summary_row = False
        for path, value in _rows(module.get("summary") or {}):
            rendered_summary_row = True
            sheet.append([_xlsx_text(path), _xlsx_scalar(value)])
        if not rendered_summary_row:
            sheet.append(["summary", ""])
        for row in sheet.iter_rows(min_row=4, max_row=sheet.max_row, min_col=1, max_col=2):
            for cell in row:
                cell.border = row_border
                cell.alignment = top_wrap_alignment
                cell.font = body_font
        sheet.column_dimensions["A"].width = 46
        sheet.column_dimensions["B"].width = 90
        sheet.sheet_properties.pageSetUpPr.fitToPage = True
        sheet.page_setup.fitToWidth = 1
        sheet.page_setup.fitToHeight = 0

    model_periods = calculation.get("periods") if isinstance(calculation.get("periods"), list) else []
    if model_periods:
        model_sheet = wb.create_sheet(_safe_sheet_name("Model", used))
        model_sheet.sheet_view.showGridLines = False
        model_sheet.freeze_panes = "A2"
        model_headers = (
            "Period key", "Label", "Kind", f"Revenue ({reporting_scale})",
            f"Adjusted EBITDA ({reporting_scale})",
            f"Cash interest ({reporting_scale})",
            f"Total debt ({reporting_scale})", f"Cash ({reporting_scale})",
            f"Net debt ({reporting_scale})", "Gross leverage",
            "Net leverage", "Interest coverage",
            f"Free cash flow ({reporting_scale})",
        )
        model_sheet.append(model_headers)
        for period in model_periods:
            if not isinstance(period, dict):
                continue
            model_sheet.append([
                _xlsx_scalar(period.get("period_key")),
                _xlsx_scalar(period.get("label")),
                _xlsx_scalar(period.get("kind")),
                period.get("revenue"), period.get("adjusted_ebitda"),
                period.get("cash_interest"), period.get("total_debt"), period.get("cash"),
                period.get("net_debt"), period.get("gross_leverage"),
                period.get("net_leverage"), period.get("interest_coverage"),
                period.get("free_cash_flow"),
            ])
        for cell in model_sheet[1]:
            cell.font = header_font
            cell.fill = navy_fill
            cell.alignment = header_alignment
        for column in range(1, len(model_headers) + 1):
            model_sheet.column_dimensions[model_sheet.cell(1, column).column_letter].width = (
                18 if column <= 3 else 16
            )
        for row in model_sheet.iter_rows(min_row=2):
            for cell in row:
                cell.border = row_border
                cell.font = body_font
            for cell in row[3:]:
                cell.number_format = "#,##0.00;[Red](#,##0.00);-"

    if override_rows or omitted_override_count:
        override_sheet = wb.create_sheet(_safe_sheet_name("Model Overrides", used))
        override_sheet.sheet_view.showGridLines = False
        override_sheet.freeze_panes = "A2"
        override_headers = (
            "Status at report event", "Node", "Override value", "Reason", "Scope",
            "Source", "Expires at", "Displaced formula", "Displaced value",
        )
        override_sheet.append(override_headers)
        for cell in override_sheet[1]:
            cell.font = header_font
            cell.fill = navy_fill
            cell.alignment = header_alignment
        for override in override_rows:
            override_sheet.append([
                _xlsx_text(override["status"]),
                _xlsx_text(override["node_id"]),
                _xlsx_scalar(override["value"]),
                _xlsx_text(override["reason"]),
                _xlsx_text(override["scope"]),
                _xlsx_text(override["source"]),
                _xlsx_text(override["expires_at"]),
                _xlsx_text(override["original_formula"]),
                _xlsx_scalar(override["original_value"]),
            ])
        if omitted_override_count:
            override_sheet.append([
                "TRUNCATED",
                f"{omitted_override_count} additional overrides remain in the frozen payload",
            ])
        for row in override_sheet.iter_rows(min_row=2):
            for cell in row:
                cell.border = row_border
                cell.alignment = top_wrap_alignment
                cell.font = body_font
        for column, width in enumerate((24, 42, 18, 48, 16, 32, 26, 52, 18), start=1):
            override_sheet.column_dimensions[
                override_sheet.cell(1, column).column_letter
            ].width = width
    del override_rows

    if model_periods:
        instrument_currencies = _instrument_currencies(model)
        debt_sheet = wb.create_sheet(_safe_sheet_name("Debt Schedule", used))
        debt_sheet.sheet_view.showGridLines = False
        debt_sheet.freeze_panes = "A2"
        debt_headers = (
            "Period key", "Instrument ID", "Instrument currency",
            f"Opening ({reporting_unit})", f"Closing ({reporting_unit})",
            f"Average ({reporting_unit})",
            f"Benchmark interest ({reporting_unit})",
            f"Margin interest ({reporting_unit})",
            f"Coupon interest ({reporting_unit})", f"Fees ({reporting_unit})",
            f"PIK interest ({reporting_unit})", f"Hedge effect ({reporting_unit})",
            f"FX effect ({reporting_unit})", f"Cash interest ({reporting_unit})",
            f"Debt in reporting currency ({reporting_scale})",
            f"Roll-forward residual ({reporting_unit})",
        )
        debt_sheet.append(debt_headers)
        for period in model_periods:
            if not isinstance(period, dict):
                continue
            instruments = period.get("instruments") if isinstance(period.get("instruments"), list) else []
            for instrument in instruments:
                if not isinstance(instrument, dict):
                    continue
                debt_sheet.append([
                    _xlsx_scalar(period.get("period_key")),
                    _xlsx_scalar(instrument.get("instrument_id")),
                    _xlsx_text(instrument_currencies.get(
                        str(instrument.get("instrument_id")), "Unavailable"
                    )),
                    instrument.get("opening_balance"), instrument.get("closing_balance"),
                    instrument.get("average_balance"), instrument.get("benchmark_interest"),
                    instrument.get("margin_interest"), instrument.get("coupon_interest"),
                    instrument.get("fees"), instrument.get("pik_interest"),
                    instrument.get("hedge_effect"), instrument.get("fx_effect"),
                    instrument.get("cash_interest"), instrument.get("debt_reporting_currency"),
                    instrument.get("rollforward_residual"),
                ])
        for cell in debt_sheet[1]:
            cell.font = header_font
            cell.fill = navy_fill
            cell.alignment = header_alignment
        for column in range(1, len(debt_headers) + 1):
            debt_sheet.column_dimensions[debt_sheet.cell(1, column).column_letter].width = (
                20 if column <= 2 else 16
            )
        for row in debt_sheet.iter_rows(min_row=2):
            for cell in row:
                cell.border = row_border
                cell.font = body_font
            for cell in row[3:]:
                cell.number_format = "#,##0.00;[Red](#,##0.00);-"

    if model:
        ledger = wb.create_sheet(_safe_sheet_name("Model Gaps - Warnings", used))
        ledger.append(["Type", "Detail"])
        for cell in ledger[1]:
            cell.font = header_font
            cell.fill = navy_fill
            cell.alignment = header_alignment
        ledger.append(["Availability", _xlsx_text(calculation.get("status") or "unknown")])
        for item in calculation.get("gaps") or []:
            ledger.append(["Gap", _xlsx_text(item)])
        for item in calculation.get("warnings") or []:
            ledger.append(["Warning", _xlsx_text(item)])
        ledger.column_dimensions["A"].width = 18
        ledger.column_dimensions["B"].width = 110

    sources = wb.create_sheet("Sources - Audit")
    sources.sheet_view.showGridLines = False
    sources.freeze_panes = "A2"
    sources.append(["Source ID", "Authority origin", "As of", "Approval state", "Freshness", "Freshness policy"])
    source_ids = authority.get("source_ids") if isinstance(authority.get("source_ids"), list) else []
    for source_id in source_ids:
        sources.append([
            _xlsx_text(source_id),
            _xlsx_text(authority.get("origin")),
            _xlsx_text(authority.get("as_of")),
            _xlsx_text(authority.get("approval_state")),
            _xlsx_text(freshness_state),
            _xlsx_text(freshness.get("policy_version")),
        ])
    if model:
        sources.append([
            _xlsx_text(f"model:{_display(model.get('calculation_hash'))}"),
            "model-engine-v2",
            _xlsx_text(authority.get("as_of")),
            _xlsx_text(authority.get("approval_state")),
            _xlsx_text(freshness_state),
            _xlsx_text(model.get("engine_version")),
        ])
    for cell in sources[1]:
        cell.font = header_font
        cell.fill = navy_fill
    for column, width in zip("ABCDEF", (54, 18, 28, 18, 14, 24)):
        sources.column_dimensions[column].width = width

    wb.properties.title = "CAOS Immutable Committee Report"
    wb.properties.subject = document_sha256
    wb.properties.creator = "CAOS Report Studio"
    wb.properties.description = f"Immutable report version {version_id}"
    output = BytesIO()
    wb.save(output)
    # Production-side structural sanity check: fail before returning malformed bytes.
    output.seek(0)
    reopened = load_workbook(output, read_only=True, data_only=False)
    if "Cover" not in reopened.sheetnames or "Module Summary" not in reopened.sheetnames:
        raise ValueError("Generated workbook failed structural verification.")
    if any(
        cell.data_type == "f"
        for sheet in reopened.worksheets
        for row in sheet.iter_rows()
        for cell in row
    ):
        raise ValueError("Generated report workbook contains executable formulas.")
    reopened.close()
    return output.getvalue()

