'use client';

import React from 'react';
import { useRemoteServer } from '@/lib/contexts/RemoteServerContext';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

const formSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  base_url: z.string().url('Must be a valid URL'),
  description: z.string().optional(),
  api_key: z.string().optional(),
  health_check_url: z.string().url('Must be a valid URL').optional().or(z.literal('')),
  username: z.string().optional(),
  password: z.string().optional(),
  auth_type: z.string().default('basic'),
  token_endpoint: z.string().url('Must be a valid URL').optional().or(z.literal('')),
});

type FormValues = z.infer<typeof formSchema>;

interface EditServerModalProps {
  server: {
    id: number;
    name: string;
    base_url: string;
    description?: string;
    api_key?: string;
    health_check_url?: string;
    username?: string;
    password?: string;
    auth_type?: 'basic' | 'token';
    token_endpoint?: string;
  };
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

export function EditServerModal({ server, open, onOpenChange, onSuccess }: EditServerModalProps) {
  const { updateServer, loading } = useRemoteServer();
  const [authType, setAuthType] = React.useState<'basic' | 'token'>(server?.auth_type || 'basic');

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: server?.name || '',
      base_url: server?.base_url || '',
      description: server?.description || '',
      api_key: server?.api_key || '',
      health_check_url: server?.health_check_url || '',
      username: server?.username || '',
      password: server?.password || '',
      auth_type: server?.auth_type || 'basic',
      token_endpoint: server?.token_endpoint || '',
    },
  });

  // Update form values when server changes
  React.useEffect(() => {
    if (server) {
      form.reset({
        name: server.name || '',
        base_url: server.base_url || '',
        description: server.description || '',
        api_key: server.api_key || '',
        health_check_url: server.health_check_url || '',
        username: server.username || '',
        password: server.password || '',
        auth_type: server.auth_type || 'basic',
        token_endpoint: server.token_endpoint || '',
      });
      setAuthType(server.auth_type || 'basic');
    }
  }, [server, form]);

  const onSubmit = async (values: FormValues) => {
    try {
      console.log('=== EDIT SERVER MODAL DEBUG ===');
      console.log('Form values:', values);
      console.log('Server ID:', server.id);
      
      if (!values.name || !values.base_url) {
        throw new Error('Name and Base URL are required');
      }

      // Only send fields that the backend RemoteServerUpdate model expects
      const serverData = {
        name: values.name,
        base_url: values.base_url,
        description: values.description || undefined,
        api_key: values.api_key || undefined,
        health_check_url: values.health_check_url || undefined,
        username: values.username || undefined,
        password: values.password || undefined,
        auth_type: (values.auth_type as 'basic' | 'token') || 'basic',
        token_endpoint: values.token_endpoint || undefined,
      };

      console.log('Prepared server data:', serverData);
      console.log('Calling updateServer...');

      await updateServer(server.id, serverData);
      console.log('Update server completed successfully');
      onSuccess?.();
    } catch (error) {
      console.error('Edit server modal error:', error);
      form.setError('root', {
        type: 'manual',
        message: error instanceof Error ? error.message : 'Failed to update server'
      });
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Edit Server</DialogTitle>
          <DialogDescription>
            Update the details of your remote server
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            {form.formState.errors.root && (
              <div className="p-3 text-sm text-red-500 bg-red-50 rounded-md">
                {form.formState.errors.root.message}
              </div>
            )}
            
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Name</FormLabel>
                  <FormControl>
                    <Input placeholder="My API Server" {...field} />
                  </FormControl>
                  <FormDescription>
                    A friendly name for your server
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
            
            <FormField
              control={form.control}
              name="base_url"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Base URL</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="https://api.example.com"
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    The base URL of your API server
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
            
            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Description</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="Optional description of the server"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            
            <FormField
              control={form.control}
              name="auth_type"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Authentication Type</FormLabel>
                  <FormControl>
                    <select
                      className="w-full p-2 border rounded-md"
                      value={field.value}
                      onChange={(e) => {
                        field.onChange(e);
                        setAuthType(e.target.value as 'basic' | 'token');
                      }}
                    >
                      <option value="basic">Basic Auth</option>
                      <option value="token">Token Auth</option>
                    </select>
                  </FormControl>
                  <FormDescription>
                    Choose the authentication method for the server
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
            
            {authType === 'basic' && (
              <>
                <FormField
                  control={form.control}
                  name="username"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Username</FormLabel>
                      <FormControl>
                        <Input
                          placeholder="Basic auth username"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="password"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Password</FormLabel>
                      <FormControl>
                        <Input
                          type="password"
                          placeholder="Basic auth password"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </>
            )}
            
            {authType === 'token' && (
              <>
                <FormField
                  control={form.control}
                  name="token_endpoint"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Token Endpoint</FormLabel>
                      <FormControl>
                        <Input
                          placeholder="https://api.example.com/oauth/token"
                          {...field}
                        />
                      </FormControl>
                      <FormDescription>
                        The endpoint for obtaining authentication tokens
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="api_key"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>API Key</FormLabel>
                      <FormControl>
                        <Input
                          type="password"
                          placeholder="API key for token authentication"
                          {...field}
                        />
                      </FormControl>
                      <FormDescription>
                        API key for authenticating with the token endpoint
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </>
            )}
            
            <FormField
              control={form.control}
              name="health_check_url"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Health Check URL</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="https://api.example.com/health"
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    Optional custom health check endpoint
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
            
            <div className="flex justify-end space-x-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
              >
                Cancel
              </Button>
              <Button 
                type="submit" 
                disabled={loading}
              >
                {loading ? 'Updating...' : 'Update'} Server
              </Button>
            </div>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
} 