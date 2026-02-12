"use client";

import { useEffect, useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import { AppShell } from "@/components/layout";
import { usePartnerStore } from "@/stores";
import { Button } from "@/components/ui/button";
import { Search, Users2, Plus, Loader2 } from "lucide-react";
import {
  PartnerCard,
  PartnerRequestCard,
  InvitationAlert,
  CreatePrivateTableModal,
  AddPartnerButton,
} from "@/components/partners";
import { toast } from "sonner";
import { useDebounce } from "@/hooks/use-debounce";

type Tab = "partners" | "requests" | "invitations";

export default function PartnersPage() {
  const t = useTranslations("partners");

  const {
    partners,
    pendingRequests,
    pendingInvitations,
    searchResults,
    isLoading,
    isSearching,
    fetchPartners,
    fetchRequests,
    fetchInvitations,
    searchUsers,
    clearSearch,
    sendRequest,
    respondToRequest,
    removePartner,
    respondToInvitation,
  } = usePartnerStore();

  const [activeTab, setActiveTab] = useState<Tab>("partners");
  const [searchQuery, setSearchQuery] = useState("");
  const [showCreateModal, setShowCreateModal] = useState(false);

  const debouncedSearch = useDebounce(searchQuery, 300);

  // Fetch all data on mount
  useEffect(() => {
    fetchPartners();
    fetchRequests();
    fetchInvitations();
  }, [fetchPartners, fetchRequests, fetchInvitations]);

  // Search when debounced query changes
  useEffect(() => {
    if (debouncedSearch.trim()) {
      searchUsers(debouncedSearch);
    } else {
      clearSearch();
    }
  }, [debouncedSearch, searchUsers, clearSearch]);

  const handleSendRequest = useCallback(
    async (userId: string) => {
      try {
        await sendRequest(userId);
        toast.success(t("requestSent"));
      } catch {
        // Error already set in store
      }
    },
    [sendRequest, t]
  );

  const handleRespondToRequest = useCallback(
    async (partnershipId: string, accept: boolean) => {
      try {
        await respondToRequest(partnershipId, accept);
        toast.success(accept ? t("requestAccepted") : t("requestDeclined"));
      } catch {
        // Error already set in store
      }
    },
    [respondToRequest, t]
  );

  const handleRemovePartner = useCallback(
    async (partnershipId: string) => {
      try {
        await removePartner(partnershipId);
        toast.success(t("partnerRemoved"));
      } catch {
        // Error already set in store
      }
    },
    [removePartner, t]
  );

  const handleRespondToInvitation = useCallback(
    async (sessionId: string, invitationId: string, accept: boolean) => {
      try {
        await respondToInvitation(sessionId, invitationId, accept);
        toast.success(accept ? t("invitationAccepted") : t("invitationDeclined"));
      } catch {
        // Error already set in store
      }
    },
    [respondToInvitation, t]
  );

  const tabs: { key: Tab; label: string }[] = [
    { key: "partners", label: t("tabs.partners") },
    { key: "requests", label: t("tabs.requests") },
    { key: "invitations", label: t("tabs.invitations") },
  ];

  const incomingRequests = pendingRequests.filter((r) => r.direction === "incoming");

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-semibold text-foreground">{t("title")}</h1>
          <p className="mt-1 text-muted-foreground">{t("subtitle")}</p>
        </div>

        {/* Tab bar */}
        <div className="flex gap-1 rounded-xl bg-muted p-1">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={
                activeTab === tab.key
                  ? "flex-1 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground transition-colors"
                  : "flex-1 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted"
              }
            >
              {tab.label}
              {tab.key === "requests" && incomingRequests.length > 0 && (
                <span className="ml-1.5 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-accent px-1 text-xs font-semibold text-accent-foreground">
                  {incomingRequests.length}
                </span>
              )}
              {tab.key === "invitations" && pendingInvitations.length > 0 && (
                <span className="ml-1.5 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-accent px-1 text-xs font-semibold text-accent-foreground">
                  {pendingInvitations.length}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Partners tab */}
        {activeTab === "partners" && (
          <div className="space-y-4">
            {/* Search bar */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={t("searchPlaceholder")}
                className="w-full rounded-xl border border-border bg-card py-2.5 pl-10 pr-4 text-sm text-foreground placeholder:text-muted-foreground focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
              />
              {isSearching && (
                <Loader2 className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin text-muted-foreground" />
              )}
            </div>

            {/* Search results */}
            {searchQuery.trim() ? (
              <div className="space-y-2">
                {isSearching ? (
                  <div className="flex items-center justify-center py-12">
                    <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                  </div>
                ) : searchResults.length > 0 ? (
                  searchResults.map((user) => (
                    <div
                      key={user.user_id}
                      className="flex items-center gap-3 rounded-xl border border-border bg-card p-3 shadow-sm"
                    >
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-accent/20 text-sm font-semibold text-accent">
                        {(user.display_name || user.username).charAt(0).toUpperCase()}
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="truncate font-medium text-foreground">
                          {user.display_name || user.username}
                        </p>
                        <p className="truncate text-sm text-muted-foreground">@{user.username}</p>
                      </div>
                      <AddPartnerButton
                        userId={user.user_id}
                        partnershipStatus={user.partnership_status}
                        onSendRequest={handleSendRequest}
                      />
                    </div>
                  ))
                ) : (
                  <div className="py-12 text-center">
                    <p className="text-sm text-muted-foreground">{t("noResults")}</p>
                  </div>
                )}
              </div>
            ) : (
              <>
                {/* Partner list */}
                {isLoading ? (
                  <div className="flex items-center justify-center py-12">
                    <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                  </div>
                ) : partners.length > 0 ? (
                  <div className="grid gap-3 md:grid-cols-2">
                    {partners.map((partner) => (
                      <PartnerCard
                        key={partner.partnership_id}
                        partner={partner}
                        onRemove={handleRemovePartner}
                      />
                    ))}
                  </div>
                ) : (
                  <div className="rounded-2xl border border-border bg-card p-8 text-center shadow-sm">
                    <Users2 className="mx-auto h-10 w-10 text-muted-foreground/50" />
                    <h3 className="mt-3 font-medium text-foreground">{t("emptyTitle")}</h3>
                    <p className="mt-1 text-sm text-muted-foreground">{t("emptySubtitle")}</p>
                  </div>
                )}

                {/* Create Private Table button */}
                {partners.length > 0 && (
                  <Button
                    variant="accent"
                    className="w-full"
                    onClick={() => setShowCreateModal(true)}
                  >
                    <Plus className="h-4 w-4" />
                    {t("createPrivateTable")}
                  </Button>
                )}
              </>
            )}
          </div>
        )}

        {/* Requests tab */}
        {activeTab === "requests" && (
          <div className="space-y-3">
            {pendingRequests.length > 0 ? (
              pendingRequests.map((request) => (
                <PartnerRequestCard
                  key={request.partnership_id}
                  request={request}
                  onRespond={handleRespondToRequest}
                />
              ))
            ) : (
              <div className="rounded-2xl border border-border bg-card p-8 text-center shadow-sm">
                <Users2 className="mx-auto h-10 w-10 text-muted-foreground/50" />
                <h3 className="mt-3 font-medium text-foreground">{t("noRequests")}</h3>
              </div>
            )}
          </div>
        )}

        {/* Invitations tab */}
        {activeTab === "invitations" && (
          <div className="space-y-3">
            {pendingInvitations.length > 0 ? (
              pendingInvitations.map((invitation) => (
                <InvitationAlert
                  key={invitation.invitation_id}
                  invitation={invitation}
                  onRespond={handleRespondToInvitation}
                />
              ))
            ) : (
              <div className="rounded-2xl border border-border bg-card p-8 text-center shadow-sm">
                <Users2 className="mx-auto h-10 w-10 text-muted-foreground/50" />
                <h3 className="mt-3 font-medium text-foreground">{t("noInvitations")}</h3>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Create Private Table Modal */}
      <CreatePrivateTableModal
        open={showCreateModal}
        onOpenChange={setShowCreateModal}
        partners={partners}
      />
    </AppShell>
  );
}
