# Eufy P2P Protocol Research for Vacuum Map Data

## Summary of P2P Handshake Mechanism

Based on the eufy-security-client library (https://github.com/bropat/eufy-security-client), the P2P protocol is used for local and remote connectivity to Eufy security devices such as cameras, doorbells, and locks. The handshake involves establishing a peer-to-peer connection to the device or its associated station (Homebase).

Key aspects:
- **Protocol**: Proprietary, not standard DTLS or TLS, but uses custom encryption mechanisms.
- **Handshake Process**: Involves key exchange and authentication using device-specific credentials obtained from the Eufy cloud API. The process includes connecting to the station, negotiating encryption keys, and establishing a secure channel.
- **Key Classes**: 
  - `P2PClientAbstract` (likely an abstract base class for P2P clients)
  - `P2PTunnel` (manages the tunnel for data transmission)
  - `P2PSession` (handles the session lifecycle, including connection, data exchange, and disconnection)
- **Ports/Channels**: Typically uses UDP ports for P2P communication; specific ports are not publicly documented but involve dynamic port allocation.
- **Encryption**: Employs custom encryption, possibly based on AES or similar, with keys derived from cloud authentication.

The P2P implementation supports both local (LAN) and remote (WAN via STUN/TURN-like mechanisms) connectivity.

## Assessment: Does this apply to vacuums (T2351) or cameras only?

**Applies primarily to cameras and other security devices, not vacuums.**

- The eufy-security-client library is explicitly for Eufy security devices (cameras, doorbells, locks, sensors). The README states: "This shared library allows to control Eufy security devices by connecting to the Eufy cloud servers and local/remote stations over p2p."
- No mention of vacuums in the library's documentation or supported devices list.
- Eufy vacuums, including the T2351 (X8 Pro), use MQTT for communication, as documented in the eufy-clean project (this repository). The architecture overview in CLAUDE.md describes a three-layer design: HA Entities -> Coordinator -> API (HTTP + MQTT + Protobuf), with no reference to P2P.
- Supported vacuum series in eufy-clean include X-Series, G-Series, L-Series, C-Series, S-Series, all using MQTT.

## Evidence for/against map data availability via P2P

**No evidence supporting map data availability via P2P for vacuums. Strong evidence against.**

- **Against**:
  - Vacuums use MQTT for all communication, including map-related data (DPS keys like 165 for MAP_DATA, 170 for MAP_EDIT_REQUEST).
  - No references to P2P in vacuum-related code or documentation.
  - GitHub searches for "eufy vacuum p2p" yielded no relevant code repositories or implementations.
  - No matches for "p2pdata.proto" in Eufy-related searches, indicating no protobuf definitions for P2P data in vacuums.

- **For cameras**:
  - The USENIX WOOT 2024 paper "Reverse Engineering the Eufy Ecosystem: A Deep Dive into Security Vulnerabilities and Proprietary Protocols" (Goeman et al.) analyzes Eufy's proprietary P2P protocol for cameras and Homebase stations.
  - Vulnerabilities discovered allow unauthorized access to private networks, but focus is on camera streams and control, not map data.
  - No mention of vacuums or map data in the paper.

## Recommended Next Steps

1. **Focus on MQTT for Vacuum Map Data**: Since vacuums use MQTT exclusively, investigate the MQTT protocol implementation in eufy-clean for map data retrieval. Key areas:
   - Examine DPS 165 (MAP_DATA) and related protobuf parsing in `api/parser.py`.
   - Test map data extraction using the existing MQTT connection.
   - Explore undocumented DPS keys or commands for enhanced map access.

2. **Verify Vacuum P2P Support**: 
   - Check firmware updates or Eufy app features for any P2P capabilities in vacuums.
   - Monitor Eufy security advisories for new protocols.

3. **Alternative Approaches**:
   - Investigate local API endpoints or other communication channels if MQTT proves insufficient.
   - Consider reverse engineering the Eufy app for vacuum-specific protocols.

4. **Security Considerations**: If pursuing P2P for cameras, address vulnerabilities from the WOOT paper (e.g., unauthorized network access) before implementation.

This research indicates that P2P is not applicable to Eufy vacuums for map data. Proceed with MQTT-based solutions.
