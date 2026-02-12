"use client";

import { useTranslations } from "next-intl";
import { ArrowLeft, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarGroup } from "@/components/ui/avatar";
import type { ConversationInfo } from "@/stores/message-store";

interface ChatHeaderProps {
  conversation: ConversationInfo;
  currentUserId: string;
  onBack: () => void;
}

function getInitials(name: string): string {
  const words = name.trim().split(/\s+/);
  return words.length >= 2
    ? (words[0][0] + words[1][0]).toUpperCase()
    : name.slice(0, 2).toUpperCase();
}

export function ChatHeader({ conversation, currentUserId, onBack }: ChatHeaderProps) {
  const t = useTranslations("messages");

  const isDirect = conversation.type === "direct";

  const partner = isDirect ? conversation.members.find((m) => m.user_id !== currentUserId) : null;

  const displayName = isDirect
    ? partner?.display_name || partner?.username || t("unknownUser")
    : conversation.name || t("groupChat");

  const memberCount = conversation.members.length;

  return (
    <div className="flex items-center gap-3 p-3 border-b border-border bg-card rounded-t-xl">
      <Button
        variant="ghost"
        size="sm"
        onClick={onBack}
        className="shrink-0 h-8 w-8 p-0"
        aria-label={t("back")}
      >
        <ArrowLeft className="size-4" />
      </Button>

      {isDirect ? (
        <Avatar className="size-8 shrink-0">
          <AvatarFallback className="text-xs bg-primary/20 text-primary">
            {getInitials(displayName)}
          </AvatarFallback>
        </Avatar>
      ) : (
        <AvatarGroup>
          {conversation.members.slice(0, 3).map((member) => (
            <Avatar key={member.user_id} size="sm" className="size-6">
              <AvatarFallback className="text-[10px] bg-primary/20 text-primary">
                {getInitials(member.display_name || member.username)}
              </AvatarFallback>
            </Avatar>
          ))}
          {memberCount > 3 && (
            <Avatar size="sm" className="size-6">
              <AvatarFallback className="text-[10px] bg-muted text-muted-foreground">
                +{memberCount - 3}
              </AvatarFallback>
            </Avatar>
          )}
        </AvatarGroup>
      )}

      <div className="flex-1 min-w-0">
        <h3 className="text-sm font-medium text-foreground truncate">{displayName}</h3>
        {!isDirect && (
          <div className="flex items-center gap-1 text-[11px] text-muted-foreground">
            <Users className="size-3" />
            <span>{t("memberCount", { count: memberCount })}</span>
          </div>
        )}
      </div>
    </div>
  );
}
