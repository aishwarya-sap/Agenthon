# Client S/4HANA OData Services — Adarsh (on-premise)

> Authoritative list of the S/4HANA OData services both agents read in the **Adarsh client
> environment**. On-premise ABAP, reached via the BTP destination **`S4HANA_DEV_HTTP`**
> (ProxyType **OnPremise** → SAP Cloud Connector, **BasicAuthentication**, technical user,
> **`sap-client=150`**). Advisory / read-only: **GET only**, `$top` capped. No POST/PATCH/DELETE.
>
> ~40 fields across 10 entity types. Everything else in these entity sets is downloaded but not used.

## The 7 services and their exact fields

### 1. Stock — `A_MatlStkInAcctMod` (`API_MATERIAL_STOCK_SRV`, on-prem `OP_API_MATERIAL_STOCK_SRV`)
- **Filter:** `Material eq '…' and Plant eq '…'`
- **Fields:** `Material, Plant, StorageLocation, InventoryStockType, InventorySpecialStockType, MatlWrhsStkQtyInMatlBaseUnit, MaterialBaseUnit`
- **Note:** stock type `01`=unrestricted, `02`=quality inspection, `03`=blocked. Only `01` counts as available.

### 2. Purchase Orders — `A_PurchaseOrderItem` (`API_PURCHASEORDER_PROCESS_SRV`)
- **Filter:** `Material eq '…'` (or `Plant eq '…'`), `$top=100`
- **Fields:** `PurchaseOrder, PurchaseOrderItem, Material, Plant, OrderQuantity, NetPriceAmount, IsCompletelyDelivered`
- **Expand `to_PurchaseOrder`:** `Supplier, PurchaseOrderDate`
- **Expand `to_ScheduleLine`:** `ScheduleLineDeliveryDate, ScheduleLineOrderQuantity`

### 3. Purchase Requisitions — `A_PurchaseRequisitionItem` (`API_PURCHASEREQ_PROCESS_SRV`)
- **Filter:** `Material eq '…'`, `$top=100`
- **Fields:** `PurchaseRequisition, PurchaseRequisitionItem, Material, Plant, RequestedQuantity, DeliveryDate, ReleaseCode, ProcessingStatus`

### 4. Goods-Receipt history — `A_MaterialDocumentItem` (`API_MATERIAL_DOCUMENT_SRV`)
- **Filter:** `Material eq '…' and Plant eq '…' and GoodsMovementType eq '101'`, `$top=4`
- **Fields:** `MaterialDocument, MaterialDocumentItem, MaterialDocumentYear, Material, Plant, GoodsMovementType, Supplier, QuantityInBaseUnit`
- **Expand `to_MaterialDocumentHeader`:** `PostingDate, ReferenceDocument`
- **Note:** a `102` cancels a `101`, so a received PO is not "silent".

### 5. Vendor / Supplier master — `A_Supplier` (`API_BUSINESS_PARTNER`)
- **Filter:** `Supplier eq '…'`
- **Fields:** `Supplier, SupplierName, SupplierFullName, PurchasingIsBlocked, SupplierAccountGroup`

### 6. Info record — `A_PurgInfoRecdOrgPlantData` (`API_INFORECORD_PROCESS_SRV`)
- **Filter:** `Material eq '…' and Plant eq '…'`
- **Fields:** `PurchasingInfoRecord, Supplier, Material, Plant, MaterialPlannedDeliveryDurn, IsMarkedForDeletion`

### 7. Purchase contract — `A_PurchaseContractItem` (`API_PURCHASECONTRACT_PROCESS_SRV`)
- **Filter:** `Material eq '…'`
- **Fields:** `PurchaseContract, PurchaseContractItem, Material, Plant, TargetQuantity`
- **Expand `to_PurchaseContract`:** `Supplier, ValidityStartDate, ValidityEndDate`

## Per-agent differences (intentional — different domains)

| Service | Material Risk | Procurement |
|---|---|---|
| **Info record** | `A_PurgInfoRecdOrgPlantData` → `PurchasingInfoRecord, Supplier, Material, Plant, MaterialPlannedDeliveryDurn, IsMarkedForDeletion` | `A_PurchasingInfoRecord` → `PurchasingInfoRecord, Supplier, AvailabilityStartDate, AvailabilityEndDate, IsRegularSupplier` |
| **Contract** | `A_PurchaseContractItem` (+ item/qty fields, expand to header) | `A_PurchaseContract` header → `PurchaseContract, ValidityStartDate, ValidityEndDate, PurchaseContractTargetAmount` |
| **Supplier** | `Supplier, SupplierName, SupplierFullName, PurchasingIsBlocked, SupplierAccountGroup` | `SupplierName, PurchasingIsBlocked` only |

Procurement additionally reads the PO **header** (`A_PurchaseOrder`: `PurchaseOrderType` ZPRJ filter,
`PurchaseOrderDate`, `Supplier`, `DocumentCurrency`) and the PR release status
(`PurReqnReleaseStatus`, `PurchaseRequisitionReleaseDate`).

## Derived fields (computed in-agent, not read from OData)

`silence_duration_days`, composite risk, float / critical-path, consequence €, risk band —
the standard OData services do not return these; the agent computes them from the raw reads above.

## Connectivity

```
BTP Destination: S4HANA_DEV_HTTP
  Type:            HTTP
  ProxyType:       OnPremise            # via SAP Cloud Connector
  Authentication:  BasicAuthentication  # technical user; PrincipalPropagation is a future switch
  URL:             http://<cloud-connector-virtual-host>:<port>
  sap-client:      150
```

- OData services must be activated on the on-prem system (`/IWFND/MAINT_SERVICE`).
- Cloud Connector must expose each service path under Cloud→On-Premise Access Control.
- The agent resolves the destination name at runtime (`S4_DESTINATION`); credentials never
  live in the repo. Bind the `destination` + `connectivity` services to the CF app.
