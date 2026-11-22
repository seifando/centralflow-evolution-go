package send_service

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"errors"
	"regexp"
	"strconv"
	"strings"
	"time"

	instance_model "github.com/evolution-foundation/evolution-go/pkg/instance/model"
	"go.mau.fi/whatsmeow"
	"go.mau.fi/whatsmeow/proto/waE2E"
	"go.mau.fi/whatsmeow/types"
	"google.golang.org/protobuf/proto"
)

var cfChannel = regexp.MustCompile(`^[0-9]{5,40}@newsletter$`)
var cfTarget = regexp.MustCompile(`^[0-9]{5,40}@(s\.whatsapp\.net|lid|g\.us|newsletter)$`)

type CentralFlowInput struct {
	JID         string `json:"jid"`
	Reference   string `json:"reference"`
	Name        string `json:"name"`
	Description string `json:"description"`
	Number      string `json:"number"`
	Type        string `json:"type"`
	Kind        string `json:"kind"`
	Text        string `json:"text"`
	Content     string `json:"content"`
	Caption     string `json:"caption"`
	Filename    string `json:"filename"`
	Base64      string `json:"base64"`
	Mime        string `json:"mime"`
	Media       *struct {
		Base64 string `json:"base64"`
		Mime   string `json:"mime"`
	} `json:"media"`
	AllContacts     bool           `json:"allContacts"`
	StatusJIDList   []string       `json:"statusJidList"`
	BackgroundColor string         `json:"backgroundColor"`
	Font            int32          `json:"font"`
	Message         *waE2E.Message `json:"message"`
}

func cfBytes(data string) ([]byte, error) {
	if len(data) > 22369624 {
		return nil, errors.New("media too large")
	}
	b, err := base64.StdEncoding.DecodeString(data)
	if err != nil || len(b) == 0 || len(b) > 16*1024*1024 {
		return nil, errors.New("invalid media")
	}
	return b, nil
}

// CentralFlow runs behind the native instance-token middleware. No global key or
// instance identifier from the body may select another account.
func (s *sendService) CentralFlow(action string, raw json.RawMessage, instance *instance_model.Instance) (any, error) {
	if action == "capabilities" {
		return map[string]any{"protocol": "centralflow-publishing/1", "provider": "evolution-go", "extensionVersion": "0.6.1", "discovery": "whatsapp_subscribed", "operations": []string{"sync", "create", "import", "refresh", "follow", "unfollow", "edit", "delete", "post", "messages"}, "selectedStatusAudience": false}, nil
	}
	var d CentralFlowInput
	if err := json.Unmarshal(raw, &d); err != nil {
		return nil, errors.New("invalid request")
	}
	client := s.clientPointer[instance.Id]
	if client == nil || !client.IsConnected() || !client.IsLoggedIn() {
		return nil, errors.New("instance disconnected")
	}
	ctx, cancel := context.WithTimeout(context.Background(), 90*time.Second)
	defer cancel()
	if strings.HasPrefix(action, "channels/") {
		op := strings.TrimPrefix(action, "channels/")
		if op == "follow" {
			if cfChannel.MatchString(d.Reference) {
				d.JID = d.Reference
			} else {
				re := regexp.MustCompile(`^https://(?:www\.)?whatsapp\.com/channel/([A-Za-z0-9_-]{5,150})/?$`)
				m := re.FindStringSubmatch(d.Reference)
				if m == nil {
					return nil, errors.New("invalid channel reference")
				}
				info, err := client.GetNewsletterInfoWithInvite(ctx, m[1])
				if err != nil {
					return nil, err
				}
				d.JID = info.ID.String()
			}
		}
		if !cfChannel.MatchString(d.JID) {
			return nil, errors.New("invalid channel id")
		}
		jid, err := types.ParseJID(d.JID)
		if err != nil {
			return nil, err
		}
		info, err := client.GetNewsletterInfo(ctx, jid)
		if err != nil {
			return nil, err
		}
		role := types.NewsletterRoleGuest
		if info.ViewerMeta != nil {
			role = info.ViewerMeta.Role
		}
		if (op == "post" || op == "edit") && role != types.NewsletterRoleOwner && role != types.NewsletterRoleAdmin {
			return nil, errors.New("channel administrator required")
		}
		if op == "delete" && role != types.NewsletterRoleOwner {
			return nil, errors.New("channel owner required")
		}
		switch op {
		case "follow":
			err = client.FollowNewsletter(ctx, jid)
		case "unfollow":
			err = client.UnfollowNewsletter(ctx, jid)
		case "edit":
			if len([]rune(d.Name)) < 2 || len([]rune(d.Name)) > 100 || len([]rune(d.Description)) > 2000 {
				return nil, errors.New("invalid channel metadata")
			}
			err = client.CentralFlowEditNewsletter(ctx, jid, d.Name, d.Description)
		case "delete":
			err = client.CentralFlowDeleteNewsletter(ctx, jid)
		case "post":
			if len([]rune(d.Text)) > 5000 {
				return nil, errors.New("text too long")
			}
			no := false
			if d.Kind == "text" {
				if d.Text == "" {
					return nil, errors.New("text required")
				}
				return s.SendText(&TextStruct{Number: d.JID, Text: d.Text, FormatJid: &no}, instance)
			}
			if d.Media == nil || (d.Kind != "image" && d.Kind != "video") {
				return nil, errors.New("invalid post media")
			}
			data, decodeErr := cfBytes(d.Media.Base64)
			if decodeErr != nil {
				return nil, decodeErr
			}
			return s.SendMediaFile(&MediaStruct{Number: d.JID, Type: d.Kind, Caption: d.Text, Filename: "publication", FormatJid: &no}, data, instance)
		default:
			return nil, errors.New("unsupported channel operation")
		}
		if err != nil {
			return nil, err
		}
		if op == "delete" || op == "unfollow" {
			return map[string]bool{"ok": true}, nil
		}
		return client.GetNewsletterInfo(ctx, jid)
	}
	switch action {
	case "media":
		if !cfTarget.MatchString(d.Number) || !regexp.MustCompile(`^(image|video|audio|document)$`).MatchString(d.Type) {
			return nil, errors.New("invalid recipient or media type")
		}
		data, err := cfBytes(d.Base64)
		if err != nil {
			return nil, err
		}
		no := false
		return s.SendMediaFile(&MediaStruct{Number: d.Number, Type: d.Type, Caption: d.Caption, Filename: d.Filename, FormatJid: &no}, data, instance)
	case "download":
		if d.Message == nil {
			return nil, errors.New("message required")
		}
		var data []byte
		var err error
		mime := "application/octet-stream"
		switch {
		case d.Message.ImageMessage != nil:
			mime = d.Message.ImageMessage.GetMimetype()
			data, err = client.Download(ctx, d.Message.ImageMessage)
		case d.Message.VideoMessage != nil:
			mime = d.Message.VideoMessage.GetMimetype()
			data, err = client.Download(ctx, d.Message.VideoMessage)
		case d.Message.AudioMessage != nil:
			mime = d.Message.AudioMessage.GetMimetype()
			data, err = client.Download(ctx, d.Message.AudioMessage)
		case d.Message.DocumentMessage != nil:
			mime = d.Message.DocumentMessage.GetMimetype()
			data, err = client.Download(ctx, d.Message.DocumentMessage)
		case d.Message.StickerMessage != nil:
			mime = d.Message.StickerMessage.GetMimetype()
			data, err = client.Download(ctx, d.Message.StickerMessage)
		default:
			return nil, errors.New("invalid media type")
		}
		if err != nil {
			return nil, err
		}
		if len(data) > 16*1024*1024 {
			return nil, errors.New("media too large")
		}
		return map[string]string{"base64": base64.StdEncoding.EncodeToString(data), "mimetype": mime}, nil
	case "status":
		// This WhatsMeow contract uses the account's status privacy. It does not
		// expose per-publication recipients. Reject narrowing requests explicitly.
		if !d.AllContacts || len(d.StatusJIDList) > 0 {
			return nil, errors.New("selected status audience unsupported by this GO contract")
		}
		if d.Type == "text" {
			if d.Content == "" || len([]rune(d.Content)) > 5000 {
				return nil, errors.New("invalid status text")
			}
			if !regexp.MustCompile(`^#[0-9a-fA-F]{6}$`).MatchString(d.BackgroundColor) || d.Font < 1 || d.Font > 5 {
				return nil, errors.New("invalid status style")
			}
			color, err := strconv.ParseUint("ff"+strings.TrimPrefix(d.BackgroundColor, "#"), 16, 32)
			if err != nil {
				return nil, err
			}
			styles := []int32{1, 2, 6, 7, 8}
			font := waE2E.ExtendedTextMessage_FontType(styles[d.Font-1])
			msg := &waE2E.Message{ExtendedTextMessage: &waE2E.ExtendedTextMessage{Text: proto.String(d.Content), BackgroundArgb: proto.Uint32(uint32(color)), Font: &font}}
			id := client.GenerateMessageID()
			_, err = client.SendMessage(ctx, types.NewJID("status", "broadcast"), msg, whatsmeow.SendRequestExtra{ID: id})
			if err != nil {
				return nil, err
			}
			return &MessageSendStruct{Info: types.MessageInfo{ID: id}, Message: msg}, nil
		}
		if d.Type != "image" && d.Type != "video" {
			return nil, errors.New("invalid status type")
		}
		return s.SendStatusMediaUrl(&StatusMediaStruct{Type: d.Type, Url: d.Content, Caption: d.Caption}, instance)
	}
	return nil, errors.New("unsupported operation")
}
