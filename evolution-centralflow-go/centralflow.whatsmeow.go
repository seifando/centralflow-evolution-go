// SPDX-License-Identifier: MPL-2.0
// Additive source file for the pinned WhatsMeow dependency. The transport and
// GraphQL error validation remain the original sendMexIQ implementation.
package whatsmeow

import (
	"context"
	"encoding/json"
	"fmt"
	"go.mau.fi/whatsmeow/types"
)

func (cli *Client) CentralFlowEditNewsletter(ctx context.Context, jid types.JID, name, description string) error {
	raw, err := cli.sendMexIQ(ctx, "24250201037901610", map[string]any{"newsletter_id": jid.String(), "updates": map[string]any{"name": name, "description": description, "settings": nil}})
	if err != nil {
		return err
	}
	var data map[string]json.RawMessage
	if err = json.Unmarshal(raw, &data); err != nil {
		return err
	}
	if v, ok := data["xwa2_newsletter_update"]; !ok || string(v) == "null" {
		return fmt.Errorf("newsletter update not acknowledged")
	}
	return nil
}
func (cli *Client) CentralFlowDeleteNewsletter(ctx context.Context, jid types.JID) error {
	raw, err := cli.sendMexIQ(ctx, "30062808666639665", map[string]any{"newsletter_id": jid.String()})
	if err != nil {
		return err
	}
	var data map[string]json.RawMessage
	if err = json.Unmarshal(raw, &data); err != nil {
		return err
	}
	if v, ok := data["xwa2_newsletter_delete_v2"]; !ok || string(v) == "null" {
		return fmt.Errorf("newsletter deletion not acknowledged")
	}
	return nil
}
