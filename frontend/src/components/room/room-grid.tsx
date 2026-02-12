"use client";

import { useRef, useState, useEffect } from "react";
import { useRoomStore } from "@/stores/room-store";
import { cn } from "@/lib/utils";
import { RoomBackground } from "./room-background";
import { RoomItem } from "./room-item";
import { CompanionSprite } from "./companion-sprite";

const GRID_COLS = 6;
const GRID_ROWS = 4;

export function RoomGrid() {
  const roomData = useRoomStore((s) => s.roomData);
  const editMode = useRoomStore((s) => s.editMode);
  const pendingLayout = useRoomStore((s) => s.pendingLayout);
  const removePlacement = useRoomStore((s) => s.removePlacement);
  const addPlacement = useRoomStore((s) => s.addPlacement);

  const gridRef = useRef<HTMLDivElement>(null);
  const [cellSize, setCellSize] = useState(80);
  const [selectedCell, setSelectedCell] = useState<{ x: number; y: number } | null>(null);

  useEffect(() => {
    const updateSize = () => {
      if (gridRef.current) {
        const width = gridRef.current.clientWidth;
        setCellSize(Math.floor(width / GRID_COLS));
      }
    };
    updateSize();
    window.addEventListener("resize", updateSize);
    return () => window.removeEventListener("resize", updateSize);
  }, []);

  const inventory = roomData?.inventory || [];
  const activeCompanion = roomData?.room.active_companion;
  const roomType = roomData?.room.room_type || "starter";
  const layout = editMode ? pendingLayout : roomData?.room.layout || [];

  // Find which inventory items are placed
  const placedItems = layout.map((placement) => {
    const inv = inventory.find((i) => i.id === placement.inventory_id);
    return { ...placement, item: inv };
  });

  // Check if a cell is occupied
  const isCellOccupied = (x: number, y: number) => {
    return placedItems.some((p) => {
      const w = p.item?.item?.size_w || 1;
      const h = p.item?.item?.size_h || 1;
      return x >= p.grid_x && x < p.grid_x + w && y >= p.grid_y && y < p.grid_y + h;
    });
  };

  const handleCellClick = (x: number, y: number) => {
    if (!editMode) return;

    // Check if clicking on an existing item
    const existingItem = placedItems.find((p) => {
      const w = p.item?.item?.size_w || 1;
      const h = p.item?.item?.size_h || 1;
      return x >= p.grid_x && x < p.grid_x + w && y >= p.grid_y && y < p.grid_y + h;
    });

    if (existingItem) {
      removePlacement(existingItem.inventory_id);
      return;
    }

    // Mark this cell as selected for the ItemPicker
    setSelectedCell({ x, y });
  };

  const handlePlaceItem = (inventoryId: string) => {
    if (!selectedCell) return;
    addPlacement({
      inventory_id: inventoryId,
      grid_x: selectedCell.x,
      grid_y: selectedCell.y,
      rotation: 0,
    });
    setSelectedCell(null);
  };

  return (
    <div className="relative w-full" ref={gridRef}>
      <RoomBackground roomType={roomType} />

      <div
        className="relative grid"
        style={{
          gridTemplateColumns: `repeat(${GRID_COLS}, ${cellSize}px)`,
          gridTemplateRows: `repeat(${GRID_ROWS}, ${cellSize}px)`,
        }}
      >
        {/* Grid cells (visible in edit mode) */}
        {editMode &&
          Array.from({ length: GRID_COLS * GRID_ROWS }).map((_, i) => {
            const x = i % GRID_COLS;
            const y = Math.floor(i / GRID_COLS);
            const occupied = isCellOccupied(x, y);
            const isSelected = selectedCell?.x === x && selectedCell?.y === y;

            return (
              <div
                key={`cell-${x}-${y}`}
                className={cn(
                  "border border-dashed transition-colors",
                  occupied ? "border-accent/30 bg-accent/5" : "border-border/50",
                  !occupied && "hover:bg-accent/10 cursor-pointer",
                  isSelected && "bg-accent/20 border-accent"
                )}
                style={{ gridColumn: x + 1, gridRow: y + 1 }}
                onClick={() => handleCellClick(x, y)}
              />
            );
          })}

        {/* Placed items */}
        {placedItems.map((p) => (
          <RoomItem
            key={p.inventory_id}
            name={p.item?.item?.name || "Item"}
            imageUrl={p.item?.item?.image_url || null}
            gridX={p.grid_x}
            gridY={p.grid_y}
            sizeW={p.item?.item?.size_w || 1}
            sizeH={p.item?.item?.size_h || 1}
            rotation={p.rotation}
            editMode={editMode}
            onClick={() => editMode && removePlacement(p.inventory_id)}
          />
        ))}
      </div>

      {/* Companion sprite */}
      {activeCompanion && !editMode && (
        <CompanionSprite
          companionType={activeCompanion}
          placements={layout}
          gridCellSize={cellSize}
        />
      )}

      {/* Item picker popover when a cell is selected */}
      {selectedCell && editMode && (
        <ItemPickerPopover
          x={selectedCell.x}
          y={selectedCell.y}
          cellSize={cellSize}
          inventory={inventory}
          placedIds={layout.map((p) => p.inventory_id)}
          onSelect={handlePlaceItem}
          onClose={() => setSelectedCell(null)}
        />
      )}
    </div>
  );
}

// Inline popover for selecting items to place
function ItemPickerPopover({
  x,
  y,
  cellSize,
  inventory,
  placedIds,
  onSelect,
  onClose,
}: {
  x: number;
  y: number;
  cellSize: number;
  inventory: Array<{ id: string; item: { name: string; image_url: string | null } | null }>;
  placedIds: string[];
  onSelect: (inventoryId: string) => void;
  onClose: () => void;
}) {
  const available = inventory.filter((inv) => !placedIds.includes(inv.id));

  if (available.length === 0) {
    return (
      <div
        className="absolute z-20 rounded-xl bg-card border border-border shadow-lg p-3 min-w-[160px]"
        style={{
          left: (x + 1) * cellSize,
          top: y * cellSize,
        }}
      >
        <p className="text-sm text-muted-foreground">No items available</p>
        <button className="mt-2 text-xs text-accent hover:underline" onClick={onClose}>
          Close
        </button>
      </div>
    );
  }

  return (
    <div
      className="absolute z-20 rounded-xl bg-card border border-border shadow-lg p-2 min-w-[160px] max-h-[200px] overflow-y-auto"
      style={{
        left: Math.min((x + 1) * cellSize, 4 * cellSize),
        top: y * cellSize,
      }}
    >
      <div className="space-y-1">
        {available.map((inv) => (
          <button
            key={inv.id}
            className="w-full flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm hover:bg-muted transition-colors text-left"
            onClick={() => onSelect(inv.id)}
          >
            <span className="text-muted-foreground text-xs">+</span>
            <span className="truncate">{inv.item?.name || "Item"}</span>
          </button>
        ))}
      </div>
      <button
        className="mt-1 w-full text-xs text-muted-foreground hover:text-foreground text-center py-1"
        onClick={onClose}
      >
        Cancel
      </button>
    </div>
  );
}
