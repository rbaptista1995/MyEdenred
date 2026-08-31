# MyEdenred for Home Assistant

Unofficial [MyEdenred Portugal](https://www.myedenred.pt/) integration for Home Assistant.

[![Release](https://img.shields.io/github/v/release/rbaptista1995/MyEdenred?style=for-the-badge&label=Release&color=blue)](https://github.com/rbaptista1995/MyEdenred/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/rbaptista1995/MyEdenred/myedenred.zip?style=for-the-badge&label=Downloads&color=brightgreen)](https://github.com/rbaptista1995/MyEdenred/releases)
[![HACS](https://img.shields.io/badge/HACS-Custom%20Repository-orange?style=for-the-badge)](https://hacs.xyz/)
[![License](https://img.shields.io/github/license/rbaptista1995/MyEdenred?style=for-the-badge)](LICENSE)
[![HACS validation](https://github.com/rbaptista1995/MyEdenred/actions/workflows/hacs.yml/badge.svg)](https://github.com/rbaptista1995/MyEdenred/actions/workflows/hacs.yml)
[![Hassfest](https://github.com/rbaptista1995/MyEdenred/actions/workflows/hassfest.yml/badge.svg)](https://github.com/rbaptista1995/MyEdenred/actions/workflows/hassfest.yml)

> **About the download count:** the badge above counts downloads of the
> `myedenred.zip` release asset across all releases. It measures file
> downloads — HACS installs, updates and reinstalls all count — and it is
> **not** a count of unique users or active installations.

## Features

- Balance and transaction sensors for each MyEdenred card
- Config-flow UI setup (username, password and 2FA code received by e-mail)
- Multiple cards supported — add the integration once per card
- Portuguese (PT) country targeting

## Installation

### HACS

The repository is not (yet) part of the HACS default repository, so add it
once as a custom repository:

1. Open **HACS** in Home Assistant
2. Click **⋮ → Custom repositories**
3. Add the repository URL:
   `https://github.com/rbaptista1995/MyEdenred`
4. Select category **Integration**
5. Search for **MyEdenred** and install it
6. Restart Home Assistant

Once included in the HACS default repository, MyEdenred can be searched
directly in HACS without adding a custom repository.

### Manual

1. Download `myedenred.zip` from the
   [latest release](https://github.com/rbaptista1995/MyEdenred/releases/latest)
2. Extract its contents into `config/custom_components/myedenred/`
3. Restart Home Assistant

## Configuration

1. Navigate to **Settings → Devices & Services** and click **Add Integration**
2. Search for **MyEdenred**
3. Enter your credentials
4. Enter the 2FA code received by e-mail
5. Repeat the procedure for each additional card you own

## Cards

Add any entity card as usual.

### Transactions

While showing the card's balance on a card is commonplace (any entity card
will do), displaying transactions can be more complicated to achieve.

#### Using a custom:html-template-card

You can use a [custom:html-template-card](https://github.com/PiotrMachowski/Home-Assistant-Lovelace-HTML-Jinja2-Template-card) to display your data like this:

```yaml
type: vertical-stack
cards:
  - type: entities
    title: Cartão Refeição
    entities:
      - entity: sensor.edenred_card_XXXXXXX
        secondary_info: last-updated
        icon: mdi:credit-card
      - entity: sensor.edenred_card_XXXXXXX
        type: custom:multiple-entity-row
        name: Nome Cartão
        show_state: false
        entities:
          - attribute: ownerName
      - entity: sensor.edenred_card_XXXXXXX
        type: custom:multiple-entity-row
        name: Estado Cartão
        show_state: false
        entities:
          - attribute: cardStatus
  - type: custom:html-template-card
    ignore_line_breaks: true
    content: |
      <table
        style="padding: 0px;border-collapse:separate;
        border:solid gray 1px;
        border-radius:6px;  ">
      <tr>
        <td  colspan="3"><center><font color="#6B8E23" size=4> <b>Últimos Movimentos: </b></center> </font></td>
      </tr>
      <tr>

      </tr>

       <tr>
          <th style="width:10%;"><u><font color=orange>Data</font></u></th>
          <th style="width:65%;"><u><font color=orange>Descrição</font></u></th>
          <th style="width:25%;"><u><font color=orange>Valor</font></u></th>
        </tr> {% for t in state_attr('sensor.edenred_card_XXXXXXX','transactions') %}

         <tr>
         <td style="border-top: 1px solid #dddddd;  text-align: center;">{{t.date}}</td>
         <td style="border-top: 1px solid #dddddd;   text-align: center;">{{t.name}}</td>
         <td style="border-top: 1px solid #dddddd;   text-align: center;"><b>{{t.amount}}</b></td>
      </div></td>
        </tr>{% endfor}</table>
```

(credits thanks to [Vítor Nóbrega](https://forum.cpha.pt/u/vpnobrega/summary)).

#### Using a custom:list-card

Another alternative is to use [custom:list-card](https://github.com/iantrich/list-card) which has the advantage of being able to indicate the number of rows to display:

```yaml
type: custom:list-card
entity: sensor.edenred_card_XXXXXXX
feed_attribute: transactions
title: MyEdenred Transactions
row_limit: 10
columns:
  - title: Data
    field: date
  - title: Movimento
    field: name
  - title: Valor
    field: amount
    postfix: ' €'
    style:
      - text-align: right
      - white-space: nowrap
```

#### Using a custom:browser-mod

If you have [custom:browser-mod](https://github.com/thomasloven/hass-browser_mod) in your system, you can show the transactions in a nice popup window, like this:
(this also uses [custom:mushroom-entity-card](https://github.com/piitaya/lovelace-mushroom) and [custom:list-card](https://github.com/iantrich/list-card))

```yaml
type: custom:mushroom-entity-card
entity: sensor.edenred_card_XXXXXXX
name: Cartão Refeição
tap_action:
    action: fire-dom-event
    browser_mod:
        command: popup
        title: MyEdenred Transactions
        style:
            .: |
            :host .content {
                width: calc(800px);
                align: center;
            }
        card:
            type: custom:list-card
            entity: sensor.edenred_card_XXXXXXX
            feed_attribute: transactions
            row_limit: 20
            columns:
            - title: Data
                field: date
            - title: Movimento
                field: name
            - title: Valor
                field: amount
                postfix: ' €'
                style:
                - text-align: right
                - white-space: nowrap
            style: |
            tr {
                height: 25px
            }
```

## Releases

Every GitHub release is automatically packaged by CI into a single
`myedenred.zip` asset containing the integration files. HACS installs and
updates from that asset.

## Legal notice

This is a personal project and isn't in any way affiliated with, sponsored
or endorsed by [MyEdenred Portugal](https://www.myedenred.pt/).

All product names, trademarks and registered trademarks in (the images in)
this repository are property of their respective owners. All images in this
repository are used by the project for identification purposes only.

The author of this project categorically rejects any and all responsibility
for the card balance and other data presented by the integration.
