# Workflow Data Validation Report

Updated: 2026-07-17

## Scope

- Birth registration domain: `C:\\Users\\ku060\\Downloads\\VAIC source\\data-pipeline\\data\\birth_procedure`
- Residence domain: `C:\\Users\\ku060\\Downloads\\VAIC source\\data-pipeline\\data\\residence_procedures`

## Step 1. Search relevant procedure codes in `full-data.csv`

### Birth registration

- Total selected procedures: 16
- Codes:
  - `2.001023`, `2.000986`, `2.000635`, `2.000522`, `2.000528`, `2.000547`, `1.004884`, `1.004772`, `1.003583`, `1.001695`, `1.001193`, `1.000893`, `1.000689`, `1.000110`, `2.000712`, `1.001020`

Validation:
- Present in `birth_procedures_summary.csv`: 16/16
- Present in `raw_data`: 16/16

### Residence management

- Total selected procedures: 13
- Codes:
  - `1.004194`, `1.004222`, `1.002755`, `1.010028`, `1.003677`, `1.010040`, `1.010041`, `1.003197`, `1.010038`, `1.010039`, `2.001159`, `1.013314`, `1.013313`

Validation:
- Present in `residence_procedures_summary.csv`: 13/13
- Present in `raw_data`: 13/13

## Step 2. Check raw-data existence

- Missing birth raw-data folders: none
- Missing residence raw-data folders: none
- No additional extraction run was required

## Step 3. Build professional decision trees from grounded data

### Birth registration pattern

- Main route groups:
  - New registration
  - Re-registration
  - Copy/extract request
  - Record note for cases handled abroad
  - Existing personal documents without valid birth registration
  - Mobile service

- Key branching variables:
  - Domestic vs abroad
  - Foreign element vs non-foreign
  - Combined parent recognition vs not combined
  - Linked BHYT and residence bundle vs standalone
  - Standard vs border vs consular vs mobile channel

### Residence management pattern

- Main route groups:
  - Register permanent residence
  - Register temporary residence
  - Extend temporary residence
  - Delete residence records
  - Absence notice
  - Lodging notice
  - Confirmation and eligibility proof
  - Data adjustment
  - Split household
  - Fallback declaration for people not yet eligible

- Key branching variables:
  - Residence goal
  - Place type: owned home vs rented/borrowed/stayed vs vehicle dwelling
  - New registration vs already registered vs not eligible

## Step 4. Output files created for backend workflow engine

- `C:\\Users\\ku060\\Downloads\\VAIC source\\data-pipeline\\data\\birth_procedure\\workflow_engine_config.json`
- `C:\\Users\\ku060\\Downloads\\VAIC source\\data-pipeline\\data\\residence_procedures\\workflow_engine_config.json`

## Validation checklist

- JSON files parse successfully
- All expected birth codes are covered: yes
- All expected residence codes are covered: yes
- Missing code lists are empty: yes
- Raw-data-backed sample procedures manually spot-checked:
  - `1.001193`
  - `2.000986`
  - `1.004194`
  - `1.013314`

## Notes for backend integration

- Backend should own `current_state`, `collected_slots`, `candidate_routes`, and `final_procedure_code`
- LLM should only:
  - parse natural language into structured slot updates
  - rewrite the current question in easy Vietnamese
  - explain why a document or next step is needed
- Final route selection should remain deterministic in backend logic
