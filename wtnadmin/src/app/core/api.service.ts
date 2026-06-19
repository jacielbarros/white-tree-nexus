import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import {
  Invitation,
  Me,
  MembershipRow,
  Organization,
  Role,
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
}
