"use client";

import { ChangeEvent, useState } from "react";

import type { CitizenGroupOption, CitizenSubdomainOption } from "../lib/types";
import { Icon } from "./Icon";

type GroupSelectorProps = {
  type: "group";
  title: string;
  description: string;
  options: CitizenGroupOption[];
  disabled?: boolean;
  onSelect: (value: string) => void;
};

type SubdomainSelectorProps = {
  type: "subdomain";
  title: string;
  description: string;
  options: CitizenSubdomainOption[];
  disabled?: boolean;
  onSelect: (value: string) => void;
};

type QuickReplySelectorProps = {
  type: "quick_reply";
  title?: string;
  description?: string;
  options: { value: string; label: string }[];
  disabled?: boolean;
  isMulti?: boolean;
  onSelect: (value: string | string[], label: string) => void;
};

type CompletedStateProps = {
  selectedLabel: string;
  helperText: string;
};

export function InlineSelectorBlock(props: GroupSelectorProps | SubdomainSelectorProps | QuickReplySelectorProps) {
  const [selectedValues, setSelectedValues] = useState<string[]>([]);
  const isMulti = props.type === "quick_reply" && props.isMulti;

  const optionKeyOf = (item: any) => {
    if (props.type === "group") return (item as CitizenGroupOption).group_key;
    if (props.type === "subdomain") return (item as CitizenSubdomainOption).subdomain_key;
    return item.value;
  };

  const optionLabelOf = (item: any) => item.label;

  function handleChange(event: ChangeEvent<HTMLSelectElement>) {
    if (isMulti) {
      const selected = Array.from(event.target.selectedOptions, (option) => option.value);
      setSelectedValues(selected);
      return;
    }

    const value = event.target.value.trim();
    if (!value) return;

    if (props.type === "quick_reply") {
      const selectedItem = (props.options as any[]).find((opt) => optionKeyOf(opt) === value);
      props.onSelect(value, selectedItem ? optionLabelOf(selectedItem) : value);
    } else {
      (props.onSelect as (value: string) => void)(value);
    }
    
    event.target.value = "";
  }

  function handleConfirmMulti() {
    if (props.type !== "quick_reply" || selectedValues.length === 0) return;
    const labels = selectedValues.map(val => {
      const opt = props.options.find(o => o.value === val);
      return opt ? opt.label : val;
    }).join(", ");
    props.onSelect(selectedValues, labels);
  }

  return (
    <div className="inline-selector">
      <div className="inline-selector-header">
        <span className="inline-selector-icon">
          <Icon name="search" />
        </span>
        <div>
          <strong>{props.title || "Lựa chọn thêm"}</strong>
        </div>
      </div>

      <label className="inline-selector-field" style={isMulti ? { flexDirection: "column", alignItems: "flex-start" } : {}}>
        <span style={isMulti ? { marginBottom: "8px" } : {}}>{props.type === "group" ? "Chọn nhóm nhu cầu" : props.type === "subdomain" ? "Chọn nhánh cụ thể" : (isMulti ? "Chọn một hoặc nhiều mục (Giữ Ctrl/Cmd để chọn nhiều)" : "Chọn một mục")}</span>
        <select 
          defaultValue={isMulti ? [] : ""} 
          onChange={handleChange} 
          disabled={props.disabled}
          multiple={isMulti}
          style={isMulti ? { height: "auto", minHeight: "120px", padding: "8px", width: "100%" } : {}}
        >
          {!isMulti && (
            <option value="" disabled>
              {props.type === "group" ? "Mở danh sách 11 nhóm Công dân" : props.type === "subdomain" ? "Mở danh sách subdomain của nhóm đã chọn" : "Mở danh sách lựa chọn"}
            </option>
          )}
          {props.options.map((item) => (
            <option key={optionKeyOf(item)} value={optionKeyOf(item)} style={isMulti ? { padding: "6px" } : {}}>
              {optionLabelOf(item)}
            </option>
          ))}
        </select>
        {isMulti && (
          <button 
            type="button" 
            onClick={handleConfirmMulti} 
            disabled={props.disabled || selectedValues.length === 0}
            className="btn-primary"
            style={{ marginTop: "12px", alignSelf: "flex-end" }}
          >
            Xác nhận
          </button>
        )}
      </label>
    </div>
  );
}

export function SelectionSummaryChip({ selectedLabel, helperText }: CompletedStateProps) {
  return (
    <div className="selection-summary-chip">
      <span>
        <Icon name="check" />
      </span>
      <div>
        <strong>{selectedLabel}</strong>
        <small>{helperText}</small>
      </div>
    </div>
  );
}
