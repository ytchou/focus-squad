"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import { Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { usePartnerStore, useMessageStore } from "@/stores";
import { toast } from "sonner";

const MAX_GROUP_MEMBERS = 3; // 3 partners + creator = 4 total

interface CreateGroupModalProps {
  open: boolean;
  onClose: () => void;
}

function getInitials(name: string): string {
  const words = name.trim().split(/\s+/);
  return words.length >= 2
    ? (words[0][0] + words[1][0]).toUpperCase()
    : name.slice(0, 2).toUpperCase();
}

export function CreateGroupModal({ open, onClose }: CreateGroupModalProps) {
  const t = useTranslations("messages");
  const [step, setStep] = useState<1 | 2>(1);
  const [groupName, setGroupName] = useState("");
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [isCreating, setIsCreating] = useState(false);

  const partners = usePartnerStore((s) => s.partners);
  const fetchPartners = usePartnerStore((s) => s.fetchPartners);
  const createGroupChat = useMessageStore((s) => s.createGroupChat);

  useEffect(() => {
    if (open) {
      fetchPartners();
      setStep(1);
      setGroupName("");
      setSelectedIds([]);
    }
  }, [open, fetchPartners]);

  const toggleMember = (userId: string) => {
    setSelectedIds((prev) => {
      if (prev.includes(userId)) {
        return prev.filter((id) => id !== userId);
      }
      if (prev.length >= MAX_GROUP_MEMBERS) return prev;
      return [...prev, userId];
    });
  };

  const handleCreate = async () => {
    if (!groupName.trim() || selectedIds.length === 0) return;

    setIsCreating(true);
    try {
      await createGroupChat(selectedIds, groupName.trim());
      toast.success(t("groupCreated"));
      onClose();
    } catch {
      toast.error(t("groupCreateFailed"));
    } finally {
      setIsCreating(false);
    }
  };

  const canProceedToStep2 = groupName.trim().length > 0;
  const canCreate = selectedIds.length > 0 && !isCreating;

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{step === 1 ? t("newGroupTitle") : t("selectMembers")}</DialogTitle>
          <DialogDescription>
            {step === 1
              ? t("newGroupDescription")
              : t("selectMembersDescription", { max: MAX_GROUP_MEMBERS })}
          </DialogDescription>
        </DialogHeader>

        {step === 1 ? (
          <div className="py-2">
            <label
              htmlFor="group-name"
              className="text-sm font-medium text-foreground mb-1.5 block"
            >
              {t("groupNameLabel")}
            </label>
            <Input
              id="group-name"
              value={groupName}
              onChange={(e) => setGroupName(e.target.value)}
              placeholder={t("groupNamePlaceholder")}
              maxLength={50}
              autoFocus
            />
            {groupName.length > 40 && (
              <p className="text-[10px] text-muted-foreground mt-1">{groupName.length}/50</p>
            )}
          </div>
        ) : (
          <div className="py-2 space-y-1 max-h-64 overflow-y-auto">
            {partners.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-4">{t("noPartners")}</p>
            ) : (
              partners.map((partner) => {
                const isSelected = selectedIds.includes(partner.user_id);
                const displayName = partner.display_name || partner.username;
                const isDisabled = !isSelected && selectedIds.length >= MAX_GROUP_MEMBERS;

                return (
                  <button
                    key={partner.user_id}
                    onClick={() => toggleMember(partner.user_id)}
                    disabled={isDisabled}
                    className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left transition-colors ${
                      isSelected
                        ? "bg-accent"
                        : isDisabled
                          ? "opacity-50 cursor-not-allowed"
                          : "hover:bg-muted/50"
                    }`}
                  >
                    <Avatar className="size-8 shrink-0">
                      <AvatarFallback className="text-xs bg-primary/20 text-primary">
                        {getInitials(displayName)}
                      </AvatarFallback>
                    </Avatar>

                    <div className="flex-1 min-w-0">
                      <span className="text-sm text-foreground truncate block">{displayName}</span>
                      <span className="text-xs text-muted-foreground">@{partner.username}</span>
                    </div>

                    {isSelected && (
                      <div className="size-5 rounded-full bg-primary flex items-center justify-center shrink-0">
                        <Check className="size-3 text-primary-foreground" />
                      </div>
                    )}
                  </button>
                );
              })
            )}

            {selectedIds.length > 0 && (
              <p className="text-xs text-muted-foreground text-center pt-2">
                {t("selectedCount", {
                  count: selectedIds.length,
                  max: MAX_GROUP_MEMBERS,
                })}
              </p>
            )}
          </div>
        )}

        <DialogFooter>
          {step === 2 && (
            <Button variant="outline" size="sm" onClick={() => setStep(1)}>
              {t("back")}
            </Button>
          )}
          {step === 1 ? (
            <Button size="sm" onClick={() => setStep(2)} disabled={!canProceedToStep2}>
              {t("next")}
            </Button>
          ) : (
            <Button size="sm" onClick={handleCreate} disabled={!canCreate}>
              {isCreating ? t("creating") : t("createGroup")}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
