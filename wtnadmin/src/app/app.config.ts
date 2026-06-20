import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { ApplicationConfig, provideBrowserGlobalErrorListeners } from '@angular/core';
import { provideRouter } from '@angular/router';
import Material from '@primeuix/themes/material';
import { MessageService } from 'primeng/api';
import { providePrimeNG } from 'primeng/config';

import { errorInterceptor } from '@app/core/error.interceptor';
import { tokenInterceptor } from '@app/core/token.interceptor';
import { routes } from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes),
    provideHttpClient(withInterceptors([tokenInterceptor, errorInterceptor])),
    providePrimeNG({ theme: { preset: Material } }),
    MessageService,
  ],
};
