import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import {
  Classification,
  ContextAnalysis,
  Diagnostic,
  DocumentVersion,
  Invitation,
  Me,
  MembershipRow,
  Organization,
  Role,
  ScopeStatement,
  Stakeholder,
  StakeholderMap,
  Suggestion,
  TokenResponse,
} from '@app/core/models';
import { environment } from '@environment/environment';

/** Cliente HTTP único da API. O token e o X-Org-Context são injetados pelo interceptor. */
@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiBaseUrl;

  // --- Auth ---
  login(email: string, password: string): Observable<TokenResponse> {
    return this.http.post<TokenResponse>(`${this.base}/auth/login`, { email, password });
  }

  logout(): Observable<void> {
    return this.http.post<void>(`${this.base}/auth/logout`, {});
  }

  me(): Observable<Me> {
    return this.http.get<Me>(`${this.base}/me`);
  }

  forgotPassword(email: string): Observable<unknown> {
    return this.http.post(`${this.base}/auth/password/forgot`, { email });
  }

  resetPassword(token: string, password: string): Observable<void> {
    return this.http.post<void>(`${this.base}/auth/password/reset`, { token, password });
  }

  acceptInvite(token: string, fullName: string, password: string): Observable<TokenResponse> {
    return this.http.post<TokenResponse>(`${this.base}/invitations/accept`, {
      token,
      full_name: fullName,
      password,
    });
  }

  // --- Organizações ---
  listOrganizations(): Observable<Organization[]> {
    return this.http.get<Organization[]>(`${this.base}/organizations`);
  }

  createOrganization(name: string, slug: string): Observable<Organization> {
    return this.http.post<Organization>(`${this.base}/organizations`, { name, slug });
  }

  changeOrgStatus(orgId: string, action: 'suspend' | 'reactivate'): Observable<Organization> {
    return this.http.patch<Organization>(`${this.base}/organizations/${orgId}/status`, { action });
  }

  // --- Usuários / vínculos (escopados pela org ativa via X-Org-Context) ---
  listUsers(): Observable<MembershipRow[]> {
    return this.http.get<MembershipRow[]>(`${this.base}/users`);
  }

  changeRole(membershipId: string, role: Role): Observable<MembershipRow> {
    return this.http.patch<MembershipRow>(`${this.base}/memberships/${membershipId}/role`, { role });
  }

  unlockUser(userId: string): Observable<void> {
    return this.http.post<void>(`${this.base}/users/${userId}/unlock`, {});
  }

  // --- Convites ---
  listInvitations(): Observable<Invitation[]> {
    return this.http.get<Invitation[]>(`${this.base}/invitations`);
  }

  createInvitation(email: string, role: Role): Observable<Invitation> {
    return this.http.post<Invitation>(`${this.base}/invitations`, { email, role });
  }

  revokeInvitation(invitationId: string): Observable<void> {
    return this.http.post<void>(`${this.base}/invitations/${invitationId}/revoke`, {});
  }

  getDiagnostic(): Observable<Diagnostic> {
    return this.http.get<Diagnostic>(`${this.base}/context/diagnostic`);
  }

  saveDiagnostic(payload: Diagnostic): Observable<Diagnostic> {
    return this.http.put<Diagnostic>(`${this.base}/context/diagnostic`, payload);
  }

  getContextAnalysis(): Observable<ContextAnalysis> {
    return this.http.get<ContextAnalysis>(`${this.base}/context/analysis`);
  }

  saveContextAnalysis(payload: { intended_outcomes: string; methodology?: string | null }): Observable<ContextAnalysis> {
    return this.http.put<ContextAnalysis>(`${this.base}/context/analysis`, payload);
  }

  createContextIssue(payload: Record<string, unknown>): Observable<unknown> {
    return this.http.post(`${this.base}/context/analysis/issues`, payload);
  }

  submitContextAnalysis(): Observable<ContextAnalysis> {
    return this.http.post<ContextAnalysis>(`${this.base}/context/analysis/submit-review`, {});
  }

  approveContextAnalysis(classification: Classification): Observable<DocumentVersion> {
    return this.http.post<DocumentVersion>(`${this.base}/context/analysis/approve`, { classification });
  }

  listContextVersions(): Observable<DocumentVersion[]> {
    return this.http.get<DocumentVersion[]>(`${this.base}/context/analysis/versions`);
  }

  getStakeholderMap(): Observable<StakeholderMap> {
    return this.http.get<StakeholderMap>(`${this.base}/context/stakeholders`);
  }

  createStakeholder(payload: Record<string, unknown>): Observable<Stakeholder> {
    return this.http.post<Stakeholder>(`${this.base}/context/stakeholders`, payload);
  }

  getScope(): Observable<ScopeStatement> {
    return this.http.get<ScopeStatement>(`${this.base}/context/scope`);
  }

  saveScope(payload: Record<string, unknown>): Observable<ScopeStatement> {
    return this.http.put<ScopeStatement>(`${this.base}/context/scope`, payload);
  }

  createScopeItem(payload: Record<string, unknown>): Observable<unknown> {
    return this.http.post(`${this.base}/context/scope/items`, payload);
  }

  getContextOverview(): Observable<Record<string, unknown>> {
    return this.http.get<Record<string, unknown>>(`${this.base}/context/overview`);
  }

  listSuggestions(): Observable<Suggestion[]> {
    return this.http.get<Suggestion[]>(`${this.base}/context/suggestions`);
  }

  acceptSuggestion(suggestionId: string): Observable<unknown> {
    return this.http.post(`${this.base}/context/suggestions/accept`, { suggestion_id: suggestionId });
  }
}
